import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { API } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Wallet, ArrowUpRight, Plus, Receipt, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { track } from "@/lib/analytics";
import { usePayments, usePaymentConfig, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { PageHead, Segmented, SectionLabel } from "@/components/kit";
import { purposeLabel } from "@/lib/labels";
import { tapMedium, tapLight, notify } from "@/lib/haptics";
import { startPayment, payErrorText } from "@/lib/payFlow";
import { PeriodTiles, OfferPerks, TrustLine, usePremiumPeriods, formatSum } from "@/components/PremiumPeriods";

const TOPUP_PACKAGES = [10000, 30000, 50000, 100000, 200000, 500000];

export default function Premium() {
  const { t, user, refresh } = useApp();
  const queryClient = useQueryClient();
  const [sp, setSearchParams] = useSearchParams();
  const tab = sp.get("tab") || "plans";
  // ?hl=vip — deep links from the privacy center land with the target plan
  // highlighted and scrolled into view.
  const hl = sp.get("hl") || "";
  useEffect(() => {
    if (!hl || tab !== "plans") return;
    const timer = setTimeout(() => {
      document.querySelector(`[data-testid="plan-${hl}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 200);
    return () => clearTimeout(timer);
  }, [hl, tab]);
  // One paid plan (Premium) is on sale. Someone who still holds the retired VIP
  // plan is shown as Premium (VIP includes everything Premium does).
  const [days, setDays] = useState(15);
  const { prices, cfg: priceCfg } = usePremiumPeriods();
  const promoOn = !!priceCfg?.women_free;
  const womenFree = user?.plan_source === "women_free";
  const hasPaid = !womenFree && ["premium", "vip"].includes(user?.plan);
  useEffect(() => { track("premium_viewed", { tab }); }, [tab]);
  const [topupAmount, setTopupAmount] = useState(50000);
  // Free-form top-up amount — the preset chips are shortcuts, not a limit.
  // CLICK can't process < 1000 so'm, so that's the real floor (backend
  // enforces the same in /payments/create for balance_topup).
  const [customTopup, setCustomTopup] = useState("");
  // Arriving here after a "click_disabled" redirect from elsewhere in the
  // app (chat unlock, boost, a plan purchase) carries the exact price that
  // was blocked - pre-fill it once so the user isn't left guessing how much
  // to transfer. Only runs on landing, so it never fights a manual edit.
  useEffect(() => {
    const amt = parseInt(sp.get("amount") || "", 10);
    if (amt > 0) setCustomTopup(String(amt));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const effectiveTopup = customTopup !== "" ? (parseInt(customTopup, 10) || 0) : topupAmount;
  const [creating, setCreating] = useState(false);
  // Manual P2P top-up (temporary CLICK fallback) — the admin toggles it and
  // sets the receiving card; while enabled, the balance tab collects a
  // card-transfer receipt instead of opening CLICK.
  const [topupCfg, setTopupCfg] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [myTopups, setMyTopups] = useState([]);
  const [submittingP2p, setSubmittingP2p] = useState(false);
  useEffect(() => {
    if (tab !== "balance") return;
    api.get("/payments/topup-config").then((r) => setTopupCfg(r.data)).catch(() => setTopupCfg({ p2p_enabled: false }));
    api.get("/payments/manual-topup/mine").then((r) => setMyTopups(r.data || [])).catch(() => {});
  }, [tab]);

  const copyCard = () => {
    const num = topupCfg?.card_number || "";
    try { navigator.clipboard.writeText(num); toast.success(t("copied")); } catch { /* older webviews */ }
  };

  const submitManualTopup = async () => {
    if (submittingP2p || effectiveTopup < 1000) return;
    if (!receipt) { toast.error(t("p2p_receipt_required")); return; }
    setSubmittingP2p(true);
    tapMedium();
    try {
      const fd = new FormData();
      fd.append("file", receipt);
      const up = await api.post("/files/upload?purpose=private", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const proof_url = `${API.replace(/\/api$/, "")}${up.data.url}`;
      await api.post("/payments/manual-topup", { amount: effectiveTopup, proof_url });
      notify("success");
      toast.success(t("p2p_sent"));
      setReceipt(null);
      const r = await api.get("/payments/manual-topup/mine");
      setMyTopups(r.data || []);
    } catch (e) {
      const d = (e?.response?.data?.detail || "").toString();
      toast.error(d === "too_many_pending" ? t("p2p_too_many") : t("error_generic"));
    } finally { setSubmittingP2p(false); }
  };
  const [showHistory, setShowHistory] = useState(false);

  const { data: payments = [] } = usePayments();
  const { data: payCfg } = usePaymentConfig();
  const payOff = !!payCfg && !payCfg.payments_available; // neither CLICK nor P2P is available
  // Only completed payments are worth showing here - a pending/expired/failed
  // attempt isn't a transaction the user needs to see in their history.
  const successfulPayments = payments.filter((p) => p.status === "success" || p.status === "paid");

  const runPayment = async (purpose, amount, months = 1, periodDays = null) => {
    setCreating(true);
    tapMedium();
    try {
      const r = await api.post("/payments/create", periodDays ? { purpose, amount, days: periodDays } : { purpose, amount, months });
      if (r.data.status === "paid") {
        notify("success");
        toast.success(t("payment_success"));
        refresh();
      } else {
        if (r.data.balance_used > 0) {
          toast.success(`${t("balance_used")}: ${Number(r.data.balance_used).toLocaleString()} ${t("sum")}`);
        }
        startPayment(r.data, t);
      }
      queryClient.invalidateQueries({ queryKey: QK.payments });
    } catch (e) {
      const detail = (e?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        setSearchParams({ tab: "balance", amount: String(amount) });
      } else {
        toast.error(payErrorText(detail, t) || t("error_generic"));
      }
    } finally { setCreating(false); }
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-10 space-y-5">
      <PageHead
        title={tab === "balance" ? t("balance_page_title") : t("premium")}
        subtitle={tab === "balance" ? t("balance_page_subtitle") : t("tagline")}
      />

      <Segmented
        value={tab}
        onChange={(k) => setSearchParams({ tab: k })}
        options={[{ key: "plans", label: t("premium_tab_plans") }, { key: "balance", label: t("premium_tab_balance") }]}
      />

      {tab === "plans" && (
        <div className="space-y-3" id="premium-plans">
          {/* Duration selector - applies to every paid plan card below.
              3/12-month terms are priced at a discount (computed against
              the 1-month rate), same numbers the "gift a subscription"
              flow already offers - this just makes it a first-class
              purchase option instead of something only discoverable via
              gifting. */}
          {payOff && (
            <div data-testid="payments-soon-banner" className="rounded-2xl border border-gold/40 bg-gold-light/25 p-3 text-[13px] leading-relaxed">
              <p className="font-semibold">{t("payments_soon_title")}</p>
              <p className="text-muted-foreground mt-0.5">{t("payments_soon_desc")}</p>
            </div>
          )}

          {!womenFree && user?.women_promo === "needs_selfie" && (
            <Link to="/verification" data-testid="women-needs-selfie" className="block rounded-3xl border-2 border-secondary/50 bg-gradient-to-b from-secondary/15 to-card p-5 space-y-2 active:scale-[0.99] transition">
              <p className="font-heading text-lg font-semibold">📸 {t("women_selfie_title")}</p>
              <p className="text-sm text-muted-foreground leading-relaxed">{t("women_selfie_desc")}</p>
              <span className="inline-block rounded-full bg-primary text-white text-sm font-semibold px-4 py-2">{t("selfie_start")}</span>
            </Link>
          )}

          {womenFree ? (
            <div className="rounded-3xl border-2 border-secondary/40 bg-gradient-to-b from-secondary/10 to-card p-5 space-y-3" data-testid="women-free-card">
              <p className="font-heading text-xl font-semibold">{t("women_free_title")}</p>
              <p className="text-sm text-muted-foreground leading-relaxed">{t("women_free_desc")}</p>
              <OfferPerks />
            </div>
          ) : hasPaid ? (
            <div className="rounded-3xl border-2 border-gold bg-gradient-to-b from-gold-light/30 to-card p-5 space-y-3" data-testid="plan-premium">
              <p className="font-heading text-xl font-semibold">💎 Premium · ✓ {t("current_plan")}</p>
              {user?.plan_until && (
                <p className="text-sm text-muted-foreground">{t("plan_active_until").replace("{date}", new Date(user.plan_until).toLocaleDateString())}</p>
              )}
              <OfferPerks />
              <p className="text-xs font-semibold pt-1">{t("plan_extend")}</p>
              <PeriodTiles prices={prices} value={days} onChange={(d) => { tapLight(); setDays(d); }} />
              <button data-testid="buy-premium" onClick={() => runPayment("premium", prices[days], 1, days)} disabled={creating || payOff} className="btn-primary">
                {t("prem_cta").replace("{price}", formatSum(prices[days]))}
              </button>
              <TrustLine />
            </div>
          ) : (
            <div className="rounded-3xl border-2 border-gold bg-gradient-to-b from-gold-light/30 to-card p-5 space-y-4" data-testid="plan-premium">
              <div>
                <p className="font-heading text-xl font-semibold">💎 {t("prem_hero_title")}</p>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{t("prem_hero_sub")}</p>
              </div>
              <PeriodTiles prices={prices} value={days} onChange={(d) => { tapLight(); setDays(d); }} />
              <OfferPerks />
              <button
                data-testid="buy-premium"
                onClick={() => { track("plan_cta_click", { plan: "premium", days }); runPayment("premium", prices[days], 1, days); }}
                disabled={creating || payOff}
                className="btn-primary"
              >
                {payOff ? t("payments_soon_cta") : t("prem_cta").replace("{price}", formatSum(prices[days]))}
              </button>
              <TrustLine />
              {promoOn && user?.gender === "male" && (
                <p className="text-[12px] text-center text-secondary font-medium" data-testid="women-active-note">{t("women_free_men_note")}</p>
              )}
            </div>
          )}

          {/* What stays free - short, so the difference is clear */}
          {!womenFree && !hasPaid && (
            <div className="rounded-3xl border border-border bg-card p-4" data-testid="plan-free">
              <p className="text-sm font-semibold">{t("plan_basic_name")} · {t("plan_free_title")}</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{t("plan_free_summary")}</p>
            </div>
          )}

          {/* Concierge — compact */}
          <Link to="/concierge" data-testid="concierge-link" className="block rounded-3xl border border-secondary/30 bg-gradient-to-br from-secondary/8 to-card p-4 active:scale-[0.99] transition">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-heading text-base font-semibold flex items-center gap-1.5">🤝 {t("concierge_title")}</p>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{t("concierge_desc")}</p>
              </div>
              <span className="shrink-0 text-xs font-semibold text-secondary inline-flex items-center gap-0.5">199,000 <ArrowUpRight className="w-3.5 h-3.5" /></span>
            </div>
          </Link>
        </div>
      )}

      {tab === "balance" && (
        <div className="space-y-4" id="premium-balance">
          {/* App balance hero — big, clear "how much do I have" */}
          <div className="rounded-3xl bg-gradient-to-br from-secondary/15 via-card to-gold-light/20 border border-secondary/25 p-5" data-testid="app-balance-card">
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <SectionLabel>{t("app_balance_title")}</SectionLabel>
                <p className="font-heading text-3xl sm:text-4xl font-semibold mt-1 tabular-nums leading-none break-words">
                  {(user.balance || 0).toLocaleString()} <span className="text-lg font-medium opacity-60">{t("sum")}</span>
                </p>
                <p className="text-[11px] text-muted-foreground mt-1.5">{t("app_balance_hint")}</p>
              </div>
              <div className="w-12 h-12 rounded-2xl bg-secondary/15 grid place-items-center shrink-0"><Wallet className="w-6 h-6 text-secondary" /></div>
            </div>
          </div>

          {/* Top-up — the PRIMARY action of this page */}
          {payOff ? (
            <div className="rounded-3xl bg-card border border-border p-5 text-center" data-testid="payments-soon-card">
              <p className="font-heading text-lg font-semibold">{t("payments_soon_title")}</p>
              <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">{t("payments_soon_desc")}</p>
            </div>
          ) : (
          <div className="rounded-3xl bg-card border border-border p-4" data-testid="topup-section">
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4 text-primary" />
              <p className="font-heading text-base font-semibold">{t("topup_choose")}</p>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3">
              {TOPUP_PACKAGES.map((v) => (
                <button
                  key={v}
                  data-testid={`topup-${v}`}
                  onClick={() => { tapLight(); setTopupAmount(v); setCustomTopup(""); }}
                  className={`rounded-2xl border py-3 text-sm font-semibold tabular-nums transition active:scale-[0.97] ${
                    customTopup === "" && topupAmount === v ? "bg-primary text-white border-primary shadow-sm" : "bg-card border-border hover:border-primary/40"
                  }`}
                >
                  {(v / 1000).toFixed(0)}k
                </button>
              ))}
            </div>
            <input
              data-testid="topup-custom"
              inputMode="numeric"
              placeholder={t("topup_custom_placeholder")}
              className="w-full mt-2 px-3.5 py-2.5 rounded-2xl border border-border bg-background text-sm tabular-nums outline-none focus:border-primary"
              value={customTopup}
              onChange={(e) => setCustomTopup(e.target.value.replace(/\D/g, ""))}
            />
            {customTopup !== "" && effectiveTopup < 1000 && (
              <p className="text-[11px] text-primary mt-1">{t("topup_min_error")}</p>
            )}
            {topupCfg?.p2p_enabled ? (
              <div className="mt-3.5 space-y-2.5" data-testid="p2p-topup">
                <p className="text-[11px] text-muted-foreground leading-relaxed">{t("p2p_topup_hint")}</p>
                <button type="button" onClick={copyCard} data-testid="p2p-card"
                  className="w-full rounded-2xl border border-secondary/40 bg-secondary/5 p-3 text-left active:scale-[0.99] transition">
                  <p className="font-heading text-lg font-semibold tabular-nums tracking-wider">
                    {(topupCfg.card_number || "").replace(/(\d{4})(?=\d)/g, "$1 ")}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {topupCfg.card_holder} · {t("copy")}
                  </p>
                </button>
                <label className={`block w-full rounded-2xl border border-dashed px-3 py-2.5 text-sm text-center cursor-pointer transition ${receipt ? "border-secondary/60 bg-secondary/10 text-secondary" : "border-border text-muted-foreground hover:border-primary/40"}`}>
                  {receipt ? `✓ ${t("p2p_receipt_attached")}` : `📎 ${t("p2p_receipt_btn")}`}
                  <input type="file" accept="image/*" className="hidden" data-testid="p2p-receipt"
                    onChange={(e) => setReceipt(e.target.files?.[0] || null)} />
                </label>
                <button
                  data-testid="p2p-submit"
                  onClick={submitManualTopup}
                  disabled={submittingP2p || effectiveTopup < 1000 || !receipt}
                  className="btn-primary"
                >
                  {submittingP2p ? "..." : `${t("p2p_submit")} · ${effectiveTopup.toLocaleString()} ${t("sum")}`}
                </button>
              </div>
            ) : (
              <>
                <button
                  data-testid="topup-pay"
                  onClick={() => runPayment("balance_topup", effectiveTopup)}
                  disabled={creating || effectiveTopup < 1000}
                  className="btn-primary mt-3.5"
                >
                  {t("pay_with_click")} · {effectiveTopup.toLocaleString()} {t("sum")}
                </button>
                <p className="text-[11px] text-muted-foreground text-center mt-2">{t("topup_click_note")}</p>
              </>
            )}
          </div>
          )}

          {/* My pending/decided manual top-up requests */}
          {topupCfg?.p2p_enabled && myTopups.length > 0 && (
            <div className="rounded-3xl bg-card border border-border p-4" data-testid="p2p-my-requests">
              <SectionLabel>{t("p2p_my_requests")}</SectionLabel>
              <div className="space-y-2 mt-2">
                {myTopups.map((r) => (
                  <div key={r.id} className="flex items-center justify-between rounded-2xl bg-muted/30 border border-border px-3 py-2.5">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold tabular-nums">{Number(r.amount).toLocaleString()} {t("sum")}</p>
                      {r.status === "rejected" && r.rejection_reason && (
                        <p className="text-[11px] text-primary mt-0.5">{r.rejection_reason}</p>
                      )}
                    </div>
                    <span className={`shrink-0 text-[11px] font-medium px-2 py-1 rounded-full ${
                      r.status === "approved" ? "bg-secondary/10 text-secondary" : r.status === "rejected" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                    }`}>
                      {r.status === "approved" ? t("status_approved_word") : r.status === "rejected" ? t("status_rejected_word") : t("status_pending_word")}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Referral earnings — shown ONLY to users who actually have referral
              money. A non-referrer never sees a withdrawal block they don't need. */}
          {(user.withdrawable_balance || 0) > 0 ? (
            <Link to="/withdrawals" data-testid="ref-earnings-card" className="block rounded-3xl bg-card border border-secondary/30 p-4 active:scale-[0.99] transition">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <SectionLabel>{t("ref_earnings_title")}</SectionLabel>
                  <p className="font-heading text-xl font-semibold mt-1 tabular-nums">{(user.withdrawable_balance || 0).toLocaleString()} <span className="text-sm font-medium opacity-60">{t("sum")}</span></p>
                  <p className="text-[11px] text-secondary mt-0.5">{t("ref_earnings_hint")}</p>
                </div>
                <span className="shrink-0 text-xs font-semibold text-primary inline-flex items-center gap-0.5">{t("withdraw_cta")} <ArrowUpRight className="w-3.5 h-3.5" /></span>
              </div>
            </Link>
          ) : (
            <Link to="/referral" data-testid="ref-earn-teaser" className="block rounded-2xl bg-muted/40 border border-border p-3.5 active:scale-[0.99] transition">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs text-muted-foreground leading-snug">{t("ref_earn_teaser")}</p>
                <span className="shrink-0 text-xs font-semibold text-secondary inline-flex items-center gap-0.5">{t("ref_title")} <ArrowUpRight className="w-3.5 h-3.5" /></span>
              </div>
            </Link>
          )}
        </div>
      )}

      {/* Payments history - collapsed behind a button, and only completed
          payments show up (a pending/expired attempt isn't useful to see). */}
      {successfulPayments.length > 0 && (
        <div>
          <button
            type="button"
            data-testid="payments-history-toggle"
            onClick={() => setShowHistory((v) => !v)}
            className="w-full flex items-center justify-between rounded-2xl bg-card border border-border p-3.5 active:scale-[0.99] transition"
          >
            <span className="text-sm font-medium inline-flex items-center gap-2"><Receipt className="w-4 h-4 text-muted-foreground" /> {t("payment_history_btn")}</span>
            <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${showHistory ? "rotate-180" : ""}`} />
          </button>
          {showHistory && (
            <div className="space-y-2 mt-2" data-testid="payments-history-list">
              {successfulPayments.slice(0, 8).map((p) => (
                <div key={p.id} className="rounded-2xl bg-card border border-border p-3 flex items-center justify-between" data-testid={`payment-${p.id}`}>
                  <div>
                    <p className="text-sm font-medium">{purposeLabel(p.purpose, t)}</p>
                    <p className="text-xs text-muted-foreground tabular-nums">{Number(p.amount || 0).toLocaleString()} {t("sum")}</p>
                  </div>
                  <span className="text-[11px] font-medium px-2 py-1 rounded-full bg-secondary/10 text-secondary">
                    {t("payment_success")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

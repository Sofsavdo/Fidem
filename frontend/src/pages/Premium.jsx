import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Crown, Check, Wallet, ArrowUpRight, Sparkles, Plus, Receipt, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { usePayments, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { PageHead, Segmented, Price, SectionLabel } from "@/components/kit";
import { purposeLabel } from "@/lib/labels";
import { tapMedium, tapLight, notify } from "@/lib/haptics";

const CHAT_UNLOCK_PRICE = 9900; // mirrors backend PRICE_CHAT_UNLOCK_UZS (comparison only)

const PLANS = [
  // The weekly free conversation belongs to the FREE tier (backend
  // FREE_WEEKLY_INITIATIONS) - paid plans have unlimited messaging, so
  // advertising "1 free chat/week" on Standard was wrong.
  { key: "free", title: "Free", price: 0, accent: "border-border",
    perks: ["profile", "candidates", "likes_matches", "chat_replies", "chat_free_weekly_perk"] },
  { key: "standard", title: "Standard", price: 34900, badge: "✅", accent: "border-secondary/50",
    perks: ["chat_unlimited", "more_filters", "privacy_hidden"] },
  { key: "premium", title: "Premium", price: 79000, badge: "💎", popular: true, accent: "border-gold",
    perks: ["chat_unlimited", "who_viewed", "who_saved", "boost_visibility", "privacy_incognito"] },
  { key: "vip", title: "VIP", price: 199000, badge: "👑", dark: true, accent: "border-white/10",
    perks: ["max_visibility", "stealth_view", "photo_peek", "priority", "family_share"] },
];

const PERK = {
  uz: { profile: "Profil", candidates: "Nomzodlar", likes_matches: "Yoqtirish va moslik", chat_replies: "Kelgan xabarga bepul javob",
    chat_unlimited: "Cheksiz yozishish", chat_free_weekly_perk: "Haftada 1 bepul suhbat boshlash", more_filters: "Ko'proq filtrlar",
    who_viewed: "Kim ko'rdi", who_saved: "Kim saqladi", boost_visibility: "Ko'rinish oshadi",
    privacy_hidden: "Maxfiy rejim (ko'rinmaslik)", privacy_incognito: "Incognito ko'rish (iz qoldirmaydi)", photo_peek: "Yopiq rasmni 5 soniya ochish",
    max_visibility: "Maksimal ko'rinish", stealth_view: "Maxfiy ko'rish", priority: "Ustuvorlik", family_share: "Oila ulashish" },
  ru: { profile: "Профиль", candidates: "Кандидаты", likes_matches: "Лайки и совпадения", chat_replies: "Бесплатный ответ на входящие",
    chat_unlimited: "Безлимит сообщений", chat_free_weekly_perk: "1 бесплатный чат в неделю", more_filters: "Больше фильтров",
    who_viewed: "Кто смотрел", who_saved: "Кто сохранил", boost_visibility: "Больше видимости",
    privacy_hidden: "Скрытый режим (невидимость)", privacy_incognito: "Инкогнито-просмотр (без следов)", photo_peek: "Открыть закрытое фото на 5 секунд",
    max_visibility: "Максимум видимости", stealth_view: "Скрытый просмотр", priority: "Приоритет", family_share: "Семейный доступ" },
  en: { profile: "Profile", candidates: "Candidates", likes_matches: "Likes & matches", chat_replies: "Free reply to incoming",
    chat_unlimited: "Unlimited messaging", chat_free_weekly_perk: "1 free chat / week", more_filters: "More filters",
    who_viewed: "Who viewed", who_saved: "Who saved", boost_visibility: "More visibility",
    privacy_hidden: "Hidden mode (invisibility)", privacy_incognito: "Incognito viewing (no traces)", photo_peek: "Open a locked photo for 5s",
    max_visibility: "Max visibility", stealth_view: "Stealth view", priority: "Priority", family_share: "Family sharing" },
};

const TOPUP_PACKAGES = [10000, 30000, 50000, 100000, 200000, 500000];

export default function Premium() {
  const { t, lang, user, refresh } = useApp();
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
  const [topupAmount, setTopupAmount] = useState(50000);
  const [creating, setCreating] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const perk = PERK[lang] || PERK.uz;

  const { data: payments = [] } = usePayments();
  // Only completed payments are worth showing here - a pending/expired/failed
  // attempt isn't a transaction the user needs to see in their history.
  const successfulPayments = payments.filter((p) => p.status === "success" || p.status === "paid");

  const runPayment = async (purpose, amount) => {
    setCreating(true);
    tapMedium();
    try {
      const r = await api.post("/payments/create", { purpose, amount });
      if (r.data.status === "paid") {
        notify("success");
        toast.success(t("payment_success"));
        refresh();
      } else {
        if (r.data.balance_used > 0) {
          toast.success(`${t("balance_used")}: ${Number(r.data.balance_used).toLocaleString()} ${t("sum")} · ${t("pay_with_click")}: ${Number(r.data.click_amount).toLocaleString()} ${t("sum")}`);
        } else {
          toast.success(t("pay_with_click"));
        }
        if (r.data.payment_link) window.open(r.data.payment_link, "_blank");
      }
      queryClient.invalidateQueries({ queryKey: QK.payments });
    } catch (e) {
      toast.error(t("error_generic"));
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
          {PLANS.map((p) => {
            const isCurrent = (user?.plan || "free") === p.key;
            return (
              <div
                key={p.key}
                data-testid={`plan-${p.key}`}
                className={`relative rounded-3xl border-2 p-4 transition ${p.accent} ${
                  p.dark ? "bg-ink text-white" : p.popular ? "bg-gradient-to-b from-gold-light/30 to-card" : "bg-card"
                } ${isCurrent ? "ring-2 ring-primary ring-offset-2 ring-offset-background" : ""} ${hl === p.key && !isCurrent ? "ring-2 ring-gold ring-offset-2 ring-offset-background" : ""}`}
              >
                {p.popular && (
                  <span className="absolute -top-2.5 left-4 inline-flex items-center gap-1 rounded-full bg-gold text-ink text-[10px] font-bold px-2.5 py-0.5 shadow-sm">
                    <Sparkles className="w-3 h-3" /> {t("plan_most_popular")}
                  </span>
                )}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="font-heading text-lg font-semibold">{p.title}</span>
                    {p.badge && <span className="text-base">{p.badge}</span>}
                  </div>
                  <div className="text-right leading-none">
                    {p.price === 0 ? (
                      <span className="font-heading text-lg font-semibold">{t("plan_free_title")}</span>
                    ) : (
                      <span className="font-heading text-lg font-semibold tabular-nums">
                        {p.price.toLocaleString()}<span className="text-xs font-medium opacity-60"> {t("sum")}{t("plan_per_month")}</span>
                      </span>
                    )}
                  </div>
                </div>

                <ul className="mt-3 grid grid-cols-1 gap-1.5">
                  {p.perks.map((k) => (
                    <li key={k} className={`text-[13px] flex items-center gap-2 ${p.dark ? "text-white/90" : "text-foreground/90"}`}>
                      <Check className={`w-3.5 h-3.5 shrink-0 ${p.dark ? "text-gold" : "text-secondary"}`} /> {perk[k] || k}
                    </li>
                  ))}
                </ul>

                {p.key !== "free" && !isCurrent && (
                  <button
                    data-testid={`buy-${p.key}`}
                    onClick={() => runPayment(p.key, p.price)}
                    disabled={creating}
                    className={`mt-3.5 w-full rounded-2xl py-2.5 text-sm font-semibold transition active:scale-[0.98] disabled:opacity-50 ${
                      p.dark ? "bg-gold text-ink" : p.popular ? "bg-gradient-to-r from-gold-dark to-gold text-ink" : "bg-primary text-white"
                    }`}
                  >
                    {t("plan_choose_cta")} · {p.price.toLocaleString()} {t("sum")}
                  </button>
                )}
                {isCurrent && (
                  <p className={`mt-3 text-xs font-semibold text-center ${p.dark ? "text-gold" : "text-secondary"}`}>
                    ✓ {t("current_plan")}
                  </p>
                )}
              </div>
            );
          })}

          {/* Value comparison — compact */}
          {(() => {
            const n = Math.ceil(34900 / CHAT_UNLOCK_PRICE);
            return (
              <div className="rounded-3xl border border-gold/30 bg-gold-light/20 p-3.5" data-testid="plan-value-compare">
                <SectionLabel className="text-gold-dark">{t("plan_compare_title")}</SectionLabel>
                <div className="mt-2.5 flex items-stretch gap-2">
                  <div className="flex-1 rounded-2xl bg-card/70 border border-border p-2.5 text-center">
                    <p className="text-sm font-semibold line-through decoration-primary/50 tabular-nums">{(n * CHAT_UNLOCK_PRICE).toLocaleString()}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{t("plan_compare_separate").replace("{n}", n)}</p>
                  </div>
                  <div className="grid place-items-center text-muted-foreground text-[11px] font-medium">vs</div>
                  <div className="flex-1 rounded-2xl bg-secondary/10 border border-secondary/30 p-2.5 text-center">
                    <p className="text-sm font-semibold text-secondary tabular-nums">34,900</p>
                    <p className="text-[10px] text-secondary/90 mt-0.5">{t("plan_compare_unlimited")}</p>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Concierge — compact */}
          <Link to="/concierge" data-testid="concierge-link" className="block rounded-3xl border border-secondary/30 bg-gradient-to-br from-secondary/8 to-card p-4 active:scale-[0.99] transition">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-heading text-base font-semibold flex items-center gap-1.5">👑 {t("concierge_title")}</p>
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
                  onClick={() => { tapLight(); setTopupAmount(v); }}
                  className={`rounded-2xl border py-3 text-sm font-semibold tabular-nums transition active:scale-[0.97] ${
                    topupAmount === v ? "bg-primary text-white border-primary shadow-sm" : "bg-card border-border hover:border-primary/40"
                  }`}
                >
                  {(v / 1000).toFixed(0)}k
                </button>
              ))}
            </div>
            <button
              data-testid="topup-pay"
              onClick={() => runPayment("balance_topup", topupAmount)}
              disabled={creating}
              className="btn-primary mt-3.5"
            >
              {t("pay_with_click")} · {topupAmount.toLocaleString()} {t("sum")}
            </button>
            <p className="text-[11px] text-muted-foreground text-center mt-2">{t("topup_click_note")}</p>
          </div>

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

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, Trophy, Medal, Gift, Wallet, Rocket } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { useLeaderboard, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { toast } from "sonner";
import { photoSrc } from "@/lib/photo";
import { Skeleton, EmptyState } from "@/components/kit";
import { tapMedium, notify } from "@/lib/haptics";
import { openExternalLink } from "@/lib/telegram";

const BOOST_PRESETS = [10000, 30000, 50000, 100000];

export default function Rankings() {
  const { t, user, refresh } = useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState("all");
  const [amount, setAmount] = useState(BOOST_PRESETS[0]);
  const [customAmount, setCustomAmount] = useState("");
  const [paying, setPaying] = useState(false);

  // Free-form amount wins over the preset chips; min 1 so'm so even a small
  // streak bonus can be contributed straight from the balance.
  const effectiveAmount = customAmount !== "" ? Math.max(0, parseInt(customAmount, 10) || 0) : amount;

  const { data: leaders = [], isLoading } = useLeaderboard(period);
  const myRank = leaders.findIndex((row) => row.user?.id === user?.id);

  const getRankBadge = (rank) => {
    if (rank === 1) return <Medal className="w-5 h-5 text-yellow-500" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-gray-400" />;
    if (rank === 3) return <Medal className="w-5 h-5 text-amber-700" />;
    return <span className="text-sm font-medium text-muted-foreground">#{rank}</span>;
  };

  const boost = async () => {
    if (paying || effectiveAmount < 1) return;
    setPaying(true);
    tapMedium();
    try {
      const r = await api.post("/payments/create", { purpose: "rank_boost", amount: effectiveAmount });
      if (r.data.status === "paid") {
        notify("success");
        toast.success(t("payment_success"));
        await refresh();
        queryClient.invalidateQueries({ queryKey: QK.leaderboard(period) });
      } else {
        if (r.data.balance_used > 0) {
          toast.success(`${t("balance_used")}: ${Number(r.data.balance_used).toLocaleString()} ${t("sum")} · ${t("pay_with_click")}: ${Number(r.data.click_amount).toLocaleString()} ${t("sum")}`);
        } else {
          toast.success(t("pay_with_click"));
        }
        if (r.data.payment_link) openExternalLink(r.data.payment_link);
      }
    } catch (e) {
      const detail = (e?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        navigate("/premium?tab=balance");
      } else {
        toast.error(detail === "click_min_1000" ? t("click_min_error") : t("error_generic"));
      }
    } finally {
      setPaying(false);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg flex items-center gap-2"><Trophy className="w-5 h-5 text-gold-dark" /> {t("top_supporters")}</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-5">
        {/* Your standing + how to climb - the page used to just show a list
            with no explanation of how to get on it. */}
        <section className="rounded-3xl bg-gradient-to-br from-gold/12 via-card to-secondary/10 border border-gold/25 p-5" data-testid="rankings-your-rank">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("rank_your_rank")}</p>
              <p className="font-heading text-2xl font-semibold mt-0.5">
                {myRank >= 0 ? `#${myRank + 1}` : t("rank_not_ranked_yet")}
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs uppercase tracking-wider text-muted-foreground inline-flex items-center gap-1 justify-end"><Wallet className="w-3.5 h-3.5" /> {t("balance")}</p>
              <p className="font-heading text-lg font-semibold tabular-nums mt-0.5">{(user?.balance || 0).toLocaleString()} {t("sum")}</p>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-border/50">
            <p className="text-xs font-medium text-muted-foreground mb-2 inline-flex items-center gap-1.5"><Rocket className="w-3.5 h-3.5" /> {t("rank_boost_hint")}</p>
            <div className="grid grid-cols-4 gap-1.5">
              {BOOST_PRESETS.map((v) => (
                <button
                  key={v}
                  data-testid={`rank-boost-${v}`}
                  onClick={() => { setAmount(v); setCustomAmount(""); }}
                  className={`rounded-xl border py-2 text-xs font-semibold tabular-nums transition ${
                    customAmount === "" && amount === v ? "bg-primary text-white border-primary" : "bg-card border-border"
                  }`}
                >
                  {(v / 1000).toFixed(0)}k
                </button>
              ))}
            </div>
            <input
              data-testid="rank-boost-custom"
              inputMode="numeric"
              placeholder={t("rank_boost_custom_placeholder")}
              className="w-full mt-1.5 px-3.5 py-2 rounded-xl border border-input bg-background text-sm tabular-nums"
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value.replace(/\D/g, ""))}
            />
            <button
              data-testid="rank-boost-pay"
              onClick={boost}
              disabled={paying || effectiveAmount < 1}
              className="w-full mt-2.5 rounded-2xl bg-gradient-to-r from-[#F0269D] to-[#8A2BE2] text-white text-sm font-semibold py-2.5 disabled:opacity-60 active:scale-[0.98] transition"
            >
              {paying ? "..." : `${t("rank_boost_cta")} · ${effectiveAmount.toLocaleString()} ${t("sum")}`}
            </button>
          </div>
        </section>

        <div className="flex gap-2 overflow-x-auto pb-2">
          {[
            ["day", t("daily")],
            ["week", t("weekly")],
            ["month", t("monthly")],
            ["all", t("all_time")],
          ].map(([k, l]) => (
            <button
              key={k}
              data-testid={`rankings-period-${k}`}
              onClick={() => setPeriod(k)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${
                period === k ? "bg-primary text-white" : "bg-muted/30 text-muted-foreground"
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        <section className="rounded-3xl border border-border bg-card p-6">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 p-3">
                  <Skeleton className="w-8 h-5 rounded-lg" />
                  <Skeleton className="w-10 h-10 rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3.5 w-1/2 rounded" />
                    <Skeleton className="h-2.5 w-1/4 rounded" />
                  </div>
                  <Skeleton className="h-4 w-16 rounded" />
                </div>
              ))}
            </div>
          ) : leaders.length === 0 ? (
            <EmptyState icon={<Trophy className="w-6 h-6" />} title={t("no_data")} hint={t("rankings_empty_hint")} />
          ) : (
            <div className="space-y-3">
              {leaders.map((row, i) => {
                const rank = i + 1;
                const mine = row.user?.id === user?.id;
                return (
                  <div
                    key={row.user?.id || i}
                    className={`flex items-center gap-3 p-3 rounded-xl ${
                      mine ? "bg-primary/8 border border-primary/30" : rank <= 3 ? "bg-gradient-to-r from-gold/10 to-transparent" : "bg-muted/30"
                    }`}
                  >
                    <div className="w-8 flex justify-center shrink-0">{getRankBadge(rank)}</div>
                    <div className="w-10 h-10 rounded-full bg-muted overflow-hidden shrink-0">
                      {row.user?.photo_url && (
                        <img loading="lazy" decoding="async" src={photoSrc(row.user.photo_url)} alt="" className="w-full h-full object-cover" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{row.user?.name || "—"}{mine ? ` (${t("me")})` : ""}</p>
                      <p className="text-xs text-muted-foreground">{row.user?.region}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold">{(row.total || 0).toLocaleString()} {t("sum")}</p>
                      <p className="text-[11px] text-muted-foreground inline-flex items-center gap-1 justify-end"><Gift className="w-3 h-3" /> {row.count || 0}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

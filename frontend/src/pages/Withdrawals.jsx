import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Wallet, ArrowDownToLine, Clock, CheckCircle2, XCircle, Info, ChevronLeft } from "lucide-react";
import { useWithdrawalsStatus, useWithdrawalsHistory, QK } from "@/hooks/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { localeFor } from "@/lib/time";

export default function Withdrawals() {
  const { t, lang } = useApp();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("");
  const [card, setCard] = useState("");
  const [holder, setHolder] = useState("");

  const { data: status } = useWithdrawalsStatus();
  const { data: history = [] } = useWithdrawalsHistory();

  const submitMutation = useMutation({
    mutationFn: ({ amt, cardNumber, holderName }) =>
      api.post("/withdrawals/request", { amount: amt, card_number: cardNumber, holder_name: holderName }),
    onSuccess: () => {
      toast.success(t("submit_request") + " ✓");
      setAmount(""); setCard(""); setHolder("");
      queryClient.invalidateQueries({ queryKey: QK.withdrawalsStatus });
      queryClient.invalidateQueries({ queryKey: QK.withdrawalsHistory });
    },
    onError: () => toast.error(t("error_generic")),
  });

  const submit = () => {
    const amt = parseInt(amount, 10);
    const minPayout = status?.min_payout || 100000;
    const maxPayout = status?.max_payout;
    if (!amt || amt < minPayout) {
      toast.error(`${t("withdraw_min_error")}: ${minPayout.toLocaleString()} ${t("sum")}`);
      return;
    }
    if (maxPayout && amt > maxPayout) {
      toast.error(`${t("withdraw_max_error")}: ${maxPayout.toLocaleString()} ${t("sum")}`);
      return;
    }
    if (amt > (status?.referral_earnings_withdrawable || 0)) {
      toast.error(t("withdraw_exceed_balance"));
      return;
    }
    if (card.replace(/\D/g, "").length < 16) {
      toast.error(t("withdraw_card_length_error"));
      return;
    }
    submitMutation.mutate({ amt, cardNumber: card, holderName: holder });
  };

  if (!status) return <div className="p-6 text-muted-foreground">{t("loading_word")}</div>;

  const statusBadge = (s) => {
    if (s === "pending") return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700"><Clock className="w-3 h-3" /> {t("status_pending_word")}</span>;
    if (s === "approved") return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 className="w-3 h-3" /> {t("status_approved_word")}</span>;
    if (s === "rejected") return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-rose-100 text-rose-700"><XCircle className="w-3 h-3" /> {t("status_rejected_word")}</span>;
    return <span className="text-xs text-muted-foreground">{s}</span>;
  };

  return (
    <div>
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="withdraw-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-semibold text-lg">{t("withdraw_title")}</span>
      </header>
      <div className="max-w-2xl mx-auto p-4 md:p-6 space-y-6">
      <p className="text-sm text-muted-foreground">{t("withdraw_explainer")}</p>

      {/* Balance card */}
      <div className="rounded-3xl border border-border bg-gradient-to-br from-primary/10 to-secondary/10 p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-2xl bg-primary text-white grid place-items-center"><Wallet className="w-5 h-5" /></div>
          <div>
            <p className="text-xs text-muted-foreground">{t("referral_earnings_withdrawable")}</p>
            <p className="text-2xl font-heading font-semibold" data-testid="withdrawable-balance">{(status?.referral_earnings_withdrawable ?? 0).toLocaleString()} {t("sum_word")}</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl bg-card p-3">
            <p className="text-muted-foreground">{t("referral_earnings_pending")}</p>
            <p className="text-sm font-medium mt-1">{(status?.referral_earnings_pending ?? 0).toLocaleString()} {t("sum_word")}</p>
          </div>
          <div className="rounded-xl bg-card p-3">
            <p className="text-muted-foreground">{t("tax_rate")}</p>
            <p className="text-sm font-medium mt-1">{status.tax_rate_pct || 12}%</p>
          </div>
        </div>
      </div>

      {/* A hover-only tooltip never shows on a touchscreen - the clarification
          (balance/gifts aren't withdrawable) needs to be plain visible text,
          and it should say something the page subtitle above hasn't already. */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Info className="w-4 h-4 shrink-0" />
        <span>{t("withdraw_only_referral")}</span>
      </div>

      {/* Eligibility */}
      <div className="rounded-3xl border border-border bg-card p-5 space-y-3">
        <h2 className="font-semibold">{t("withdraw_eligibility")}</h2>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            {status?.paid_referrals_count >= 3 ? (
              <CheckCircle2 className="w-4 h-4 text-secondary" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-500" />
            )}
            <span className={status?.paid_referrals_count >= 3 ? "text-secondary" : "text-muted-foreground"}>
              {t("withdraw_requires_paid")} ({status?.paid_referrals_count || 0}/3)
            </span>
          </div>
          <div className="flex items-center gap-2">
            {status?.verified_identity ? (
              <CheckCircle2 className="w-4 h-4 text-secondary" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-500" />
            )}
            <span className={status?.verified_identity ? "text-secondary" : "text-muted-foreground"}>
              {t("withdraw_requires_verification")}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {status?.account_age_days >= 30 ? (
              <CheckCircle2 className="w-4 h-4 text-secondary" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-500" />
            )}
            <span className={status?.account_age_days >= 30 ? "text-secondary" : "text-muted-foreground"}>
              {t("withdraw_requires_age")} 30 {t("days")} ({status?.account_age_days || 0}/30)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{t("withdraw_min_payout")}: 100,000 {t("sum")}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{t("withdraw_tax")}: {status?.tax_rate_pct || 12}%</span>
          </div>
        </div>
      </div>

      {/* Request form */}
      <div className="rounded-3xl border border-border bg-card p-5 space-y-3">
        <h2 className="font-semibold">{t("request_withdraw")}</h2>
        <input
          data-testid="withdraw-amount"
          type="number"
          placeholder={`${t("amount_uzs")} (min ${(status?.min_payout ?? 100000).toLocaleString()}${status?.max_payout ? `, max ${status.max_payout.toLocaleString()}` : ""})`}
          className="w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <input
          data-testid="withdraw-card"
          inputMode="numeric"
          placeholder={t("card_number") + " (16)"}
          className="w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm font-mono"
          value={card}
          onChange={(e) => setCard(e.target.value.replace(/[^\d ]/g, ""))}
          maxLength={19}
        />
        <input
          data-testid="withdraw-holder"
          placeholder={t("name")}
          className="w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm"
          value={holder}
          onChange={(e) => setHolder(e.target.value)}
        />
        <button
          data-testid="withdraw-submit"
          onClick={submit}
          disabled={submitMutation.isPending || (status.referral_earnings_withdrawable || 0) < (status.min_payout || 100000)}
          className="w-full py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <ArrowDownToLine className="w-4 h-4" />
          {submitMutation.isPending ? "..." : t("submit_request")}
        </button>
      </div>

      {/* History */}
      <div className="rounded-3xl border border-border bg-card p-5">
        <h2 className="font-semibold mb-3">{t("payout_history")}</h2>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("no_requests_yet")}</p>
        ) : (
          <div className="space-y-2">
            {history.map((w) => (
              <div key={w.id} className="py-2 border-b border-border/40 last:border-0">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{(w.amount || 0).toLocaleString()} {t("sum_word")}</p>
                    <p className="text-[11px] text-muted-foreground">{w.created_at ? new Date(w.created_at).toLocaleString(localeFor(lang)) : "—"}</p>
                    <p className="text-[11px] text-muted-foreground font-mono">**** **** **** {(w.card_number || "").slice(-4)}</p>
                  </div>
                  {statusBadge(w.status)}
                </div>
                {w.status === "rejected" && (
                  <div
                    data-testid={`withdraw-reject-reason-${w.id}`}
                    className="mt-2 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 px-3 py-2"
                  >
                    {w.rejection_reason && (
                      <p className="text-xs text-rose-700 dark:text-rose-300">
                        <span className="font-semibold">{t("withdraw_reject_reason_label")}:</span> {w.rejection_reason}
                      </p>
                    )}
                    <p className="text-[11px] text-rose-600/80 dark:text-rose-400/80 mt-0.5">{t("withdraw_reject_refund_note")}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}

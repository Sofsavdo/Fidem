import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Wallet, ArrowDownToLine, Clock, CheckCircle2, XCircle, Info } from "lucide-react";

export default function Withdrawals() {
  const { t } = useApp();
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [amount, setAmount] = useState("");
  const [card, setCard] = useState("");
  const [holder, setHolder] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      const [s, h] = await Promise.all([api.get("/withdrawals/status"), api.get("/withdrawals/mine")]);
      setStatus(s.data);
      setHistory(h.data || []);
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    const amt = parseInt(amount, 10);
    if (!amt || amt < (status?.min_payout || 100000)) {
      toast.error(`${t("withdraw_min_error")}: ${(status?.min_payout || 100000).toLocaleString()} ${t("sum")}`);
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
    setLoading(true);
    try {
      await api.post("/withdrawals/request", { amount: amt, card_number: card, holder_name: holder });
      toast.success(t("submit_request") + " ✓");
      setAmount(""); setCard(""); setHolder("");
      load();
    } catch (e) {
      toast.error(t("error_generic"));
    } finally { setLoading(false); }
  };

  if (!status) return <div className="p-6 text-muted-foreground">{t("loading_word")}</div>;

  const statusBadge = (s) => {
    if (s === "pending") return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700"><Clock className="w-3 h-3" /> {t("status_pending_word")}</span>;
    if (s === "approved") return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 className="w-3 h-3" /> {t("status_approved_word")}</span>;
    if (s === "rejected") return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-rose-100 text-rose-700"><XCircle className="w-3 h-3" /> {t("status_rejected_word")}</span>;
    return <span className="text-xs text-muted-foreground">{s}</span>;
  };

  return (
    <div className="max-w-2xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-semibold">{t("withdraw_title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t("withdraw_explainer")}</p>
      </div>

      {/* Balance card */}
      <div className="rounded-3xl border border-border bg-gradient-to-br from-primary/10 to-secondary/10 p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-2xl bg-primary text-white grid place-items-center"><Wallet className="w-5 h-5" /></div>
          <div>
            <p className="text-xs text-muted-foreground">{t("referral_earnings_withdrawable")}</p>
            <p className="text-2xl font-heading font-semibold" data-testid="withdrawable-balance">{(status.referral_earnings_withdrawable || 0).toLocaleString()} {t("sum_word")}</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl bg-card p-3">
            <p className="text-muted-foreground">{t("referral_earnings_pending")}</p>
            <p className="text-sm font-medium mt-1">{(status.referral_earnings_pending || 0).toLocaleString()} {t("sum_word")}</p>
          </div>
          <div className="rounded-xl bg-card p-3">
            <p className="text-muted-foreground">{t("tax_rate")}</p>
            <p className="text-sm font-medium mt-1">{status.tax_rate_pct || 12}%</p>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="rounded-2xl border border-border bg-card p-4 flex gap-3 text-sm">
        <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div className="text-muted-foreground">
          <p>{t("withdraw_explainer")}</p>
        </div>
      </div>

      {/* Request form */}
      <div className="rounded-3xl border border-border bg-card p-5 space-y-3">
        <h2 className="font-semibold">{t("request_withdraw")}</h2>
        <input
          data-testid="withdraw-amount"
          type="number"
          placeholder={`${t("amount_uzs")} (min ${(status.min_payout || 100000).toLocaleString()})`}
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
          disabled={loading || (status.referral_earnings_withdrawable || 0) < (status.min_payout || 100000)}
          className="w-full py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <ArrowDownToLine className="w-4 h-4" />
          {loading ? "..." : t("submit_request")}
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
              <div key={w.id} className="flex items-center justify-between py-2 border-b border-border/40 last:border-0">
                <div>
                  <p className="text-sm font-medium">{(w.amount).toLocaleString()} {t("sum_word")}</p>
                  <p className="text-[11px] text-muted-foreground">{new Date(w.created_at).toLocaleString()}</p>
                  <p className="text-[11px] text-muted-foreground font-mono">**** **** **** {(w.card_number || "").slice(-4)}</p>
                </div>
                {statusBadge(w.status)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

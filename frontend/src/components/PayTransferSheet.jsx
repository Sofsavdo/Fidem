// Card-transfer payment (Hamyon): shows the card and the EXACT amount, counts
// down the 5-minute window and follows the payment until it is confirmed.
// Opened from anywhere through lib/payFlow.startPayment().
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, Copy, CreditCard, Loader2, X, Clock } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { notify, tapLight } from "@/lib/haptics";
import { track } from "@/lib/analytics";
import { PAY_EVENT, PAID_EVENT } from "@/lib/payFlow";
import { openSupportChat } from "@/lib/support";

const groupDigits = (n) => String(n ?? "").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
const formatCard = (c) => String(c || "").replace(/\s+/g, "").replace(/(\d{4})(?=\d)/g, "$1 ");

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Older Telegram webviews: fall back to a hidden textarea.
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

export default function PayTransferSheet() {
  const { t, refresh } = useApp();
  const queryClient = useQueryClient();
  const [pay, setPay] = useState(null);
  const [status, setStatus] = useState("pending");
  const [left, setLeft] = useState(0);
  const [cancelling, setCancelling] = useState(false);
  const deadline = useRef(0);

  useEffect(() => {
    const open = (e) => {
      const d = e.detail || {};
      deadline.current = Date.now() + (d.expires_in || 300) * 1000;
      setLeft(d.expires_in || 300);
      setStatus(d.status === "pending" || d.status === "prepared" ? "pending" : d.status || "pending");
      setPay(d);
      track("pay_transfer_opened", { purpose: d.purpose });
    };
    window.addEventListener(PAY_EVENT, open);
    return () => window.removeEventListener(PAY_EVENT, open);
  }, []);

  const finishPaid = useCallback(async () => {
    notify("success");
    track("pay_transfer_paid", { purpose: pay?.purpose });
    window.dispatchEvent(new CustomEvent(PAID_EVENT, { detail: pay }));
    queryClient.invalidateQueries();
    try { await refresh(); } catch { /* the next load picks it up */ }
  }, [pay, queryClient, refresh]);

  // Countdown.
  useEffect(() => {
    if (!pay || status !== "pending") return undefined;
    const id = setInterval(() => setLeft(Math.max(0, Math.round((deadline.current - Date.now()) / 1000))), 1000);
    return () => clearInterval(id);
  }, [pay, status]);

  // Follow the payment: the server also asks Hamyon directly, so this ends
  // even if a callback was lost. Keeps polling a bit past the 5 minutes,
  // because a transfer made in the last seconds is confirmed slightly later.
  useEffect(() => {
    if (!pay || status !== "pending") return undefined;
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.get(`/payments/status/${pay.id}`);
        if (stop) return;
        const s = r.data?.status;
        if (s === "success" || s === "paid") {
          setStatus("success");
          finishPaid();
        } else if (s === "cancelled" || s === "expired" || s === "failed") {
          if (Date.now() > deadline.current - 1000 || s !== "cancelled") setStatus("expired");
          else setStatus("cancelled");
        }
      } catch { /* network blip: try again next tick */ }
    };
    const id = setInterval(tick, 4000);
    tick();
    return () => { stop = true; clearInterval(id); };
  }, [pay, status, finishPaid]);

  if (!pay) return null;

  const close = () => {
    if (status === "pending") toast.info(t("pay_bg_note"));
    setPay(null);
  };

  const cancel = async () => {
    if (cancelling) return;
    if (!window.confirm(t("pay_cancel_confirm"))) return;
    setCancelling(true);
    try {
      const r = await api.post(`/payments/cancel/${pay.id}`);
      if (r.data?.status === "success") { setStatus("success"); finishPaid(); }
      else setStatus("cancelled");
      queryClient.invalidateQueries();
      try { await refresh(); } catch { /* ignore */ }
    } catch {
      toast.error(t("error_generic"));
    } finally {
      setCancelling(false);
    }
  };

  const copy = async (text) => {
    tapLight();
    if (await copyText(text)) toast.success(t("copied"));
  };

  const bumped = (pay.pay_amount || 0) - ((pay.amount || 0) - (pay.balance_used || 0));
  const mm = Math.floor(left / 60);
  const ss = String(left % 60).padStart(2, "0");

  return (
    <div className="fixed inset-0 flex items-end" style={{ zIndex: 10002 }} data-testid="pay-sheet">
      <div className="absolute inset-0 bg-black/50" />
      <div
        className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-5 max-h-[92vh] overflow-y-auto"
        style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))" }}
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading text-xl font-semibold">
            {status === "success" ? t("pay_success_title")
              : status === "expired" ? t("pay_expired_title")
              : status === "cancelled" ? t("pay_cancelled_title")
              : t("pay_transfer_title")}
          </h3>
          <button data-testid="pay-close" onClick={close} className="p-2 rounded-full hover:bg-muted" aria-label={t("pay_close")}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {status === "success" && (
          <div className="text-center py-6" data-testid="pay-success">
            <div className="w-16 h-16 rounded-full bg-secondary/15 grid place-items-center mx-auto">
              <Check className="w-8 h-8 text-secondary" />
            </div>
            <p className="text-sm text-muted-foreground mt-3">{t("pay_success_desc")}</p>
            <button className="btn-primary mt-5" onClick={() => setPay(null)}>{t("pay_close")}</button>
          </div>
        )}

        {(status === "expired" || status === "cancelled") && (
          <div className="text-center py-5" data-testid="pay-ended">
            <p className="text-sm text-muted-foreground leading-relaxed">
              {status === "expired" ? t("pay_expired_desc") : t("pay_cancelled_desc")}
            </p>
            {status === "expired" && (
              <button
                type="button"
                data-testid="pay-support"
                onClick={openSupportChat}
                className="w-full mt-4 rounded-2xl border border-border py-3 text-sm font-medium hover:bg-muted transition"
              >
                {t("contact_admin")}
              </button>
            )}
            <button className="btn-primary mt-3" onClick={() => setPay(null)}>{t("pay_close")}</button>
          </div>
        )}

        {status === "pending" && (
          <div className="space-y-3">
            <button
              type="button"
              data-testid="pay-amount"
              onClick={() => copy(String(pay.pay_amount))}
              className="w-full rounded-2xl border border-primary/40 bg-primary/5 p-4 text-left active:scale-[0.99] transition"
            >
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">{t("pay_amount_label")}</span>
              <span className="flex items-center justify-between gap-2 mt-1">
                <span className="font-heading text-3xl font-semibold tabular-nums">
                  {groupDigits(pay.pay_amount)} <span className="text-base font-medium opacity-60">{t("sum")}</span>
                </span>
                <Copy className="w-5 h-5 text-primary shrink-0" />
              </span>
            </button>
            <p className="text-[12px] leading-relaxed text-primary font-medium" data-testid="pay-exact-hint">
              {t("pay_exact_hint")}
              {bumped > 0 && <> {t("pay_bumped_hint").replace("{n}", bumped)}</>}
            </p>

            <button
              type="button"
              data-testid="pay-card"
              onClick={() => copy(String(pay.card).replace(/\s+/g, ""))}
              className="w-full rounded-2xl border border-border p-4 text-left active:scale-[0.99] transition"
            >
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">{t("pay_card_label")}</span>
              <span className="flex items-center justify-between gap-2 mt-1">
                <span className="flex items-center gap-2 font-heading text-xl font-semibold tabular-nums tracking-wider">
                  <CreditCard className="w-5 h-5 text-muted-foreground" />
                  {formatCard(pay.card)}
                </span>
                <Copy className="w-5 h-5 text-primary shrink-0" />
              </span>
            </button>

            <ol className="text-[13px] text-muted-foreground space-y-1.5 pl-1">
              <li>1. {t("pay_step_1")}</li>
              <li>2. {t("pay_step_2")}</li>
              <li>3. {t("pay_step_3")}</li>
            </ol>

            <div className="flex items-center justify-between rounded-2xl bg-muted/60 px-4 py-3" data-testid="pay-waiting">
              <span className="flex items-center gap-2 text-sm font-medium">
                <Loader2 className="w-4 h-4 animate-spin" /> {t("pay_waiting")}
              </span>
              <span className="flex items-center gap-1 text-sm tabular-nums font-semibold">
                <Clock className="w-4 h-4" /> {mm}:{ss}
              </span>
            </div>

            <button
              type="button"
              data-testid="pay-cancel"
              onClick={cancel}
              disabled={cancelling}
              className="w-full rounded-2xl border border-border py-3 text-sm font-medium text-muted-foreground hover:bg-muted transition"
            >
              {cancelling ? "..." : t("pay_cancel")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

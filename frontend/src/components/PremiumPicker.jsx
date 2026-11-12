// Quick Premium sheet opened from any upsell (who liked me, chat paywall,
// filters...): pick 1 day / 15 days / 1 month and pay in one tap, without
// leaving the screen the person was on.
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { X } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { track } from "@/lib/analytics";
import { notify, tapMedium } from "@/lib/haptics";
import { startPayment, payErrorText } from "@/lib/payFlow";
import { PICKER_EVENT } from "@/lib/purchase";
import { PeriodTiles, OfferPerks, TrustLine, usePremiumPeriods, formatSum } from "@/components/PremiumPeriods";

export default function PremiumPicker() {
  const [open, setOpen] = useState(null);
  useEffect(() => {
    const h = (e) => {
      setOpen(e.detail || {});
      track("premium_picker_opened", { source: e.detail?.source });
    };
    window.addEventListener(PICKER_EVENT, h);
    return () => window.removeEventListener(PICKER_EVENT, h);
  }, []);
  // The sheet (and its price request) only exists while it is open, so
  // signed-out pages never call the authenticated price endpoint.
  return open ? <PickerSheet open={open} setOpen={setOpen} /> : null;
}

function PickerSheet({ open, setOpen }) {
  const { t, refresh } = useApp();
  const navigate = useNavigate();
  const { prices } = usePremiumPeriods();
  const [days, setDays] = useState(15);
  const [busy, setBusy] = useState(false);

  const buy = async () => {
    if (busy) return;
    setBusy(true);
    tapMedium();
    track("plan_cta_click", { plan: "premium", days, source: open.source });
    try {
      const r = await api.post("/payments/create", { purpose: "premium", days });
      setOpen(null);
      if (r.data?.status === "paid") {
        notify("success");
        toast.success(t("payment_success"));
        await refresh();
        open.onPaid?.();
      } else {
        startPayment(r.data, t);
      }
    } catch (e) {
      const detail = (e?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        setOpen(null);
        navigate(`/premium?tab=balance&amount=${prices[days]}`);
      } else {
        toast.error(payErrorText(detail, t) || t("error_generic"));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-end" style={{ zIndex: 10001 }} data-testid="premium-picker">
      <div className="absolute inset-0 bg-black/45" onClick={() => setOpen(null)} />
      <div className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-5 space-y-4 max-h-[92vh] overflow-y-auto"
        style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))" }}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-heading text-xl font-semibold">💎 {t("picker_title")}</h3>
            {open.reason && <p className="text-sm text-muted-foreground mt-1">{open.reason}</p>}
          </div>
          <button onClick={() => setOpen(null)} className="p-2 rounded-full hover:bg-muted" aria-label={t("pay_close")} data-testid="premium-picker-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <PeriodTiles prices={prices} value={days} onChange={setDays} />
        <OfferPerks compact />
        <button data-testid="premium-picker-buy" onClick={buy} disabled={busy} className="btn-primary">
          {busy ? "..." : t("prem_cta").replace("{price}", formatSum(prices[days]))}
        </button>
        <TrustLine />
      </div>
    </div>
  );
}

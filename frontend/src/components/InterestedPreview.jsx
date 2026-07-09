import React, { useState } from "react";
import { Lock, MapPin, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useSavedSummary, QK } from "@/hooks/queries";
import { tapMedium, notify } from "@/lib/haptics";

// Cheapest plan that includes "who viewed / who saved me" — mirrors
// PLANS.premium in Premium.jsx (Standard does not include this perk).
const UNLOCK_PLAN = { key: "premium", price: 79000 };

// Replaces the old "N viewed / saved -> /premium" redirect banner: shows the
// real (masked) list right here, and unlocking happens in place instead of
// bouncing to the generic plans page.
export default function InterestedPreview() {
  const { t, user, refresh } = useApp();
  const queryClient = useQueryClient();
  const { data } = useSavedSummary();
  const [openId, setOpenId] = useState(null);
  const [paying, setPaying] = useState(false);

  if (["premium", "vip"].includes(user?.plan)) return null;
  if (!data || !data.total) return null;

  const { items = [], total } = data;
  const extra = Math.max(0, total - items.length);

  const unlock = async () => {
    if (paying) return;
    setPaying(true);
    tapMedium();
    try {
      const r = await api.post("/payments/create", { purpose: UNLOCK_PLAN.key, amount: UNLOCK_PLAN.price });
      if (r.data.status === "paid") {
        notify("success");
        toast.success(t("payment_success"));
        await refresh();
        queryClient.invalidateQueries({ queryKey: QK.savedSummary });
        setOpenId(null);
      } else {
        if (r.data.payment_link) window.open(r.data.payment_link, "_blank");
        toast.success(t("pay_with_click"));
      }
    } catch {
      toast.error(t("error_generic"));
    } finally {
      setPaying(false);
    }
  };

  const UnlockRow = () => (
    <div className="px-4 pb-4 pt-1">
      <div className="rounded-2xl bg-primary/6 border border-primary/25 p-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium leading-snug">{t("who_viewed_unlock_hint")}</p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {t("premium")} · {UNLOCK_PLAN.price.toLocaleString()} {t("sum")}{t("plan_per_month")}
          </p>
        </div>
        <button
          data-testid="interested-pay-btn"
          onClick={unlock}
          disabled={paying}
          className="shrink-0 rounded-full bg-gradient-to-r from-[#F0269D] to-[#8A2BE2] text-white text-xs font-semibold px-3.5 py-2 active:scale-[0.97] transition disabled:opacity-60"
        >
          {paying ? "..." : t("plan_choose_cta")}
        </button>
      </div>
    </div>
  );

  return (
    <div className="rounded-3xl bg-card border border-border overflow-hidden" data-testid="interested-preview">
      <div className="px-4 pt-4 pb-2">
        <p className="font-heading text-base font-semibold">{t("profile_teaser_title")}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{t("profile_teaser_subtitle").replace("{n}", total)}</p>
      </div>
      <div className="divide-y divide-border">
        {items.map((c) => (
          <div key={c.id}>
            <button
              type="button"
              data-testid={`interested-row-${c.id}`}
              onClick={() => setOpenId(openId === c.id ? null : c.id)}
              className="w-full flex items-center gap-3 px-4 py-3 active:bg-muted/60 transition text-left"
            >
              <div className="w-11 h-11 rounded-full bg-muted grid place-items-center shrink-0">
                <Lock className="w-4 h-4 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{c.name}, {c.age}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1 truncate">
                  <MapPin className="w-3 h-3 shrink-0" /> <span className="truncate">{c.region || "—"}</span>
                </p>
              </div>
              <ChevronRight className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${openId === c.id ? "rotate-90" : ""}`} />
            </button>
            {openId === c.id && <UnlockRow />}
          </div>
        ))}
      </div>
      {extra > 0 && (
        <>
          <button
            type="button"
            data-testid="interested-more"
            onClick={() => setOpenId(openId === "more" ? null : "more")}
            className="w-full flex items-center justify-between px-4 py-3 border-t border-border active:bg-muted/60 transition"
          >
            <span className="text-sm text-muted-foreground">*** {t("and_n_more").replace("{n}", extra)}</span>
            <span className="text-[11px] font-semibold text-primary">{t("profile_teaser_cta")}</span>
          </button>
          {openId === "more" && <div className="border-t border-border"><UnlockRow /></div>}
        </>
      )}
    </div>
  );
}

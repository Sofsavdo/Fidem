// The Premium offer, shared by the Premium page and the quick picker sheet:
// three periods (1 day / 15 days / 1 month) with the per-day price and the
// saving against buying day by day, plus one clear call to action.
import React from "react";
import { Check } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { usePaymentConfig } from "@/hooks/queries";
import { PREMIUM_PERIODS_DEFAULT } from "@/lib/purchase";

export const PERIOD_KEYS = [1, 15, 30];

export function usePremiumPeriods() {
  const { data: cfg } = usePaymentConfig();
  const fromServer = cfg?.premium_periods;
  const prices = {};
  for (const d of PERIOD_KEYS) prices[d] = Number(fromServer?.[String(d)]) || PREMIUM_PERIODS_DEFAULT[d];
  return { prices, cfg };
}

const fmt = (n) => Number(n || 0).toLocaleString("ru-RU").replace(/ /g, " ");

export function PeriodTiles({ prices, value, onChange }) {
  const { t } = useApp();
  const daily = prices[1];
  return (
    <div className="grid grid-cols-3 gap-2" data-testid="premium-periods">
      {PERIOD_KEYS.map((d) => {
        const perDay = Math.round(prices[d] / d);
        const save = d > 1 ? Math.round((1 - prices[d] / (daily * d)) * 100) : 0;
        const active = value === d;
        return (
          <button
            key={d}
            type="button"
            data-testid={`period-${d}`}
            onClick={() => onChange(d)}
            className={`relative rounded-2xl border-2 px-2 pt-4 pb-2.5 text-center transition active:scale-[0.97] ${
              active ? "border-primary bg-primary/5 shadow-sm" : "border-border bg-card"
            }`}
          >
            <span className={`absolute -top-2.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full px-2 py-0.5 text-[9px] font-bold ${
              d === 15 ? "bg-gold text-ink" : d === 30 ? "bg-secondary text-white" : "bg-muted text-muted-foreground"
            }`}>
              {t(`period_${d}d_tag`)}
            </span>
            <span className="block font-heading text-sm font-semibold">{t(`period_${d}d`)}</span>
            <span className="block font-heading text-base font-bold tabular-nums mt-1">{fmt(prices[d])}</span>
            <span className="block text-[10px] text-muted-foreground">{t("sum")}</span>
            <span className="block text-[10px] text-muted-foreground mt-1 tabular-nums">{t("per_day").replace("{n}", fmt(perDay))}</span>
            {save > 0 && (
              <span className="block text-[10px] font-semibold text-secondary mt-0.5">{t("save_vs_daily").replace("{n}", save)}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export const OFFER_PERKS = ["chat_unlimited", "who_liked", "contact_share", "family_contact", "ai_compat", "boost_visibility"];

export function OfferPerks({ compact = false }) {
  const { t } = useApp();
  const keys = compact ? OFFER_PERKS.slice(0, 4) : OFFER_PERKS;
  return (
    <ul className="grid grid-cols-1 gap-1.5" data-testid="premium-perks">
      {keys.map((k) => (
        <li key={k} className="text-[13px] flex items-center gap-2 text-foreground/90">
          <Check className="w-3.5 h-3.5 shrink-0 text-secondary" /> {t(`perk_${k}`)}
        </li>
      ))}
    </ul>
  );
}

export function TrustLine() {
  const { t } = useApp();
  return (
    <p className="text-[11px] text-muted-foreground text-center leading-relaxed" data-testid="premium-trust">
      {t("prem_instant")} · {t("prem_no_autorenew")}
    </p>
  );
}

export { fmt as formatSum };

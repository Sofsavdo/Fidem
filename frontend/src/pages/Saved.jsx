import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApp } from "@/contexts/AppContext";
import { Lock, Bookmark, Crown } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { useSaved } from "@/hooks/queries";
import { EmptyState } from "@/components/kit";

const TABS = [
  { k: "mine", labelKey: "saved_by_me" },
  { k: "by_others", labelKey: "saved_me" },
  { k: "viewers", labelKey: "viewed_my_profile" },
  { k: "interested", labelKey: "interested_in_me" },
];

// Cheapest plan that unlocks these lists — mirrors PLANS.premium in Premium.jsx.
const UNLOCK_PRICE = 79000;

export default function Saved() {
  const { t, user } = useApp();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState("mine");

  useEffect(() => {
    const q = searchParams.get("tab");
    if (q && TABS.some((x) => x.k === q)) setTab(q);
  }, [searchParams]);

  const { data: items = [], isLoading } = useSaved(tab);
  const isPremium = ["premium", "vip"].includes(user?.plan);
  const hasLocked = useMemo(() => items.some((c) => c.locked), [items]);
  const showPlanPromo = tab !== "mine" && !isPremium && hasLocked;

  const selectTab = useCallback((k) => {
    setTab(k);
    if (k === "mine") {
      setSearchParams({}, { replace: true });
    } else {
      setSearchParams({ tab: k }, { replace: true });
    }
  }, [setSearchParams]);

  return (
    <div className="px-4 md:px-8 pt-6">
      <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight mb-4">{t("liked")}</h1>
      <div className="flex gap-1 mb-4 overflow-x-auto no-scrollbar -mx-4 px-4">
        {TABS.map((x) => (
          <button
            key={x.k}
            data-testid={`saved-tab-${x.k}`}
            onClick={() => selectTab(x.k)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs border transition ${
              tab === x.k ? "bg-foreground text-background border-foreground" : "bg-card border-border"
            }`}
          >
            {t(x.labelKey)}
          </button>
        ))}
      </div>

      {showPlanPromo && (
        <Link
          to="/premium?tab=plans"
          data-testid="saved-plan-promo"
          className="mb-4 flex items-center justify-between gap-3 rounded-3xl bg-gradient-to-r from-ink to-zinc-800 text-white p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform"
        >
          <div className="min-w-0">
            <p className="font-heading text-base font-semibold flex items-center gap-1.5"><Crown className="w-4 h-4 text-gold" /> {t("who_viewed_unlock_hint")}</p>
            <p className="text-xs text-white/70 mt-0.5">{t("premium")} · {UNLOCK_PRICE.toLocaleString()} {t("sum")}{t("plan_per_month")}</p>
          </div>
          <span className="shrink-0 rounded-full bg-white text-ink text-xs font-semibold px-3.5 py-2">{t("plan_choose_cta")}</span>
        </Link>
      )}

      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="aspect-[4/5] rounded-3xl bg-muted animate-pulse" />
          ))}
        </div>
      )}
      {!isLoading && items.length === 0 && (
        <div data-testid="saved-empty">
          <EmptyState icon={<Bookmark className="w-6 h-6" />} title={t("saved_empty_title")} hint={t("saved_empty_hint")} />
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 stagger" data-testid="saved-grid">
        {items.map((c, idx) => {
          if (c.locked) {
            // Age + region stay visible (masked name, locked photo) — a real
            // teaser instead of a blank card, consistent with Me's preview.
            return (
              <div key={`locked-${tab}-${idx}`} className="aspect-[4/5] rounded-3xl bg-card border border-border overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-b from-muted to-card flex flex-col items-center justify-center text-center p-4">
                  <Lock className="w-6 h-6 text-muted-foreground" />
                  <p className="text-sm font-medium mt-2">{c.name}, {c.age}</p>
                  <p className="text-[11px] text-muted-foreground">{c.region}</p>
                  <Link data-testid="locked-upgrade" to="/premium?tab=plans" className="mt-3 text-xs font-medium text-foreground underline">{t("upgrade")}</Link>
                </div>
              </div>
            );
          }

          const photoLocked = c.photo_unlocked !== true;
          const photoUrl = photoLocked ? null : photoSrc(c.photo_url);

          return (
            <Link
              key={c.id}
              to={`/candidate/${c.id}`}
              data-testid={`saved-card-${c.id}`}
              className="block aspect-[4/5] rounded-3xl bg-card border border-border overflow-hidden relative hover:shadow-elevated transition-shadow"
            >
              {photoUrl ? (
                <img src={photoUrl} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="absolute inset-0 bg-muted flex flex-col items-center justify-center">
                  <Lock className="w-6 h-6 text-muted-foreground" />
                  {photoLocked && (
                    <p className="text-[10px] text-muted-foreground mt-2 px-2 text-center">{t("photo_locked")}</p>
                  )}
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0 pointer-events-none" />
              <div className="absolute bottom-2 left-3 right-3 text-white pointer-events-none">
                <p className="font-medium text-sm">{c.name}, {c.age}</p>
                <p className="text-[10px] text-white/85">{c.region}</p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

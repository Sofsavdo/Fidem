import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useApp } from "@/contexts/AppContext";
import { ArrowLeft, Gift as GiftIcon, Sparkles } from "lucide-react";
import { useGiftsCatalog } from "@/hooks/queries";

const TIER_META = {
  care:   { label_uz: "Atash",        label_ru: "Знаки",       label_en: "Cares",     cls: "bg-rose-100 text-rose-700" },
  love:   { label_uz: "Sevish",      label_ru: "Любовь",      label_en: "Love",      cls: "bg-pink-100 text-pink-700" },
  luxury: { label_uz: "Hashamat",    label_ru: "Люкс",        label_en: "Luxury",    cls: "bg-gold-light text-gold-dark" },
};

const TIER_ORDER = ["care", "love", "luxury"];

export default function Gifts() {
  const { user, t, lang } = useApp();
  const [activeTier, setActiveTier] = useState("care");

  const { data: catalog, isLoading } = useGiftsCatalog();

  const groups = useMemo(() => {
    if (!catalog) return {};
    const g = { care: [], love: [], luxury: [] };
    (catalog.items || []).forEach((it) => {
      if (g[it.tier]) g[it.tier].push(it);
    });
    return g;
  }, [catalog]);

  const labelKey = lang === "ru" ? "label_ru" : lang === "en" ? "label_en" : "label_uz";
  const balance = user?.balance || 0;
  const freeRemaining = catalog?.free_remaining ?? 0;

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-semibold tracking-tight flex items-center gap-2">
            <GiftIcon className="w-6 h-6 text-foreground" /> {t("gift_shop_title")}
          </h1>
          <p className="text-xs text-muted-foreground">{t("gift_shop_subtitle")}</p>
        </div>
      </div>

      {/* Balance info */}
      <div className="flex items-center justify-between gap-2 px-4 py-3 rounded-2xl bg-muted/40 text-sm">
        <span className="text-muted-foreground">{t("gift_balance_label")}: <b className="text-foreground">{balance.toLocaleString()} {t("sum")}</b></span>
        <span className="inline-flex items-center gap-1 text-emerald-700">
          <Sparkles className="w-4 h-4" /> {t("gift_free_remaining")}: {freeRemaining} / {catalog?.free_quota_per_week || 1}
        </span>
      </div>

      {/* Tier tabs */}
      <div className="flex gap-2 overflow-x-auto no-scrollbar">
        {TIER_ORDER.map((tk) => {
          const tm = TIER_META[tk];
          const active = activeTier === tk;
          return (
            <button
              key={tk}
              onClick={() => setActiveTier(tk)}
              className={`whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium border transition ${
                active ? "bg-foreground text-background border-foreground" : "bg-card border-border"
              }`}
            >
              {tm[labelKey]} <span className="opacity-60">({(groups[tk] || []).length})</span>
            </button>
          );
        })}
      </div>

      {/* Gifts grid */}
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {isLoading && <p className="col-span-full text-center text-sm text-muted-foreground py-6">{t("loading")}</p>}
        {(groups[activeTier] || []).map((g) => {
          const cannotAfford = balance < g.price;
          return (
            <div
              key={g.kind}
              className={`rounded-2xl border p-4 transition flex flex-col items-center gap-2 ${
                cannotAfford ? "border-border bg-muted/20 opacity-50" : "border-border bg-card hover:-translate-y-1 hover:shadow-lg"
              }`}
            >
              <span className="text-5xl leading-none">{g.emoji}</span>
              <span className="text-xs font-medium text-center leading-tight">{g[labelKey]}</span>
              <span className="text-[11px] text-muted-foreground">
                {g.price >= 1000 ? `${(g.price / 1000).toFixed(g.price >= 10000 ? 0 : 1)}K` : g.price} {t("sum")}
              </span>
            </div>
          );
        })}
      </div>

      {/* Tip */}
      <div className="text-center text-xs text-muted-foreground py-4">
        {t("gift_tip")}
      </div>
    </div>
  );
}

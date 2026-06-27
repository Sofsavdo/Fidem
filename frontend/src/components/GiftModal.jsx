import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { X, Gift as GiftIcon, Sparkles } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

const TIER_META = {
  free:   { label_uz: "Bepul",       label_ru: "Бесплатно",   label_en: "Free",      cls: "bg-emerald-100 text-emerald-700" },
  care:   { label_uz: "Atash",        label_ru: "Знаки",       label_en: "Cares",     cls: "bg-rose-100 text-rose-700" },
  love:   { label_uz: "Sevish",      label_ru: "Любовь",      label_en: "Love",      cls: "bg-pink-100 text-pink-700" },
  luxury: { label_uz: "Hashamat",    label_ru: "Люкс",        label_en: "Luxury",    cls: "bg-gold-light text-gold-dark" },
};

const TIER_ORDER = ["free", "care", "love", "luxury"];

export default function GiftModal({ targetId, targetName, onClose, onSent }) {
  const { user, t, lang, refresh } = useApp();
  const [catalog, setCatalog] = useState(null);
  const [sending, setSending] = useState(null);
  const [activeTier, setActiveTier] = useState("free");

  useEffect(() => {
    if (!targetId) return;
    api.get("/gifts/catalog").then((r) => setCatalog(r.data)).catch(() => {});
  }, [targetId]);

  const groups = useMemo(() => {
    if (!catalog) return {};
    const g = { free: [], care: [], love: [], luxury: [] };
    (catalog.items || []).forEach((it) => {
      if (g[it.tier]) g[it.tier].push(it);
    });
    return g;
  }, [catalog]);

  if (!targetId) return null;

  const labelKey = lang === "ru" ? "label_ru" : lang === "en" ? "label_en" : "label_uz";

  const send = async (item) => {
    setSending(item.kind);
    try {
      const r = await api.post("/gifts/send", { to_user_id: targetId, gift_kind: item.kind });
      const isFree = r.data?.gift?.is_free;
      toast.success(isFree ? `${item.emoji} ${item[labelKey]} bepul yuborildi!` : `${item.emoji} yuborildi ✓`);
      await refresh();
      onSent?.(item.kind);
      onClose();
    } catch (e) {
      toast.error("Xato yuz berdi");
    } finally {
      setSending(null);
    }
  };

  const freeRemaining = catalog?.free_remaining ?? 0;
  const balance = user?.balance || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center" data-testid="gift-modal">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full sm:max-w-lg bg-card rounded-t-3xl sm:rounded-3xl shadow-2xl animate-fade-up max-h-[88vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border/40 shrink-0">
          <div>
            <h3 className="font-heading text-lg font-semibold flex items-center gap-2">
              <GiftIcon className="w-5 h-5 text-primary" /> Sovg'a yuborish
            </h3>
            {targetName && <p className="text-xs text-muted-foreground">→ {targetName}</p>}
          </div>
          <button data-testid="gift-modal-close" onClick={onClose} className="p-2 rounded-full hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Balance info */}
        <div className="flex items-center justify-between gap-2 px-4 py-2.5 bg-muted/40 text-xs">
          <span className="text-muted-foreground">Balans: <b className="text-foreground">{balance.toLocaleString()} so'm</b></span>
          <span className="inline-flex items-center gap-1 text-emerald-700">
            <Sparkles className="w-3 h-3" /> Bepul qoldiq: {freeRemaining} / {catalog?.free_quota_per_week || 1}
          </span>
        </div>

        {/* Tier tabs */}
        <div className="flex gap-1 px-3 py-2 overflow-x-auto no-scrollbar shrink-0 border-b border-border/40">
          {TIER_ORDER.map((tk) => {
            const tm = TIER_META[tk];
            const active = activeTier === tk;
            return (
              <button
                key={tk}
                data-testid={`gift-tier-${tk}`}
                onClick={() => setActiveTier(tk)}
                className={`whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium border transition ${
                  active ? "bg-foreground text-background border-foreground" : "bg-card border-border"
                }`}
              >
                {tm[labelKey]} <span className="opacity-60">({(groups[tk] || []).length})</span>
              </button>
            );
          })}
        </div>

        {/* Gifts grid - scrollable */}
        <div className="overflow-y-auto p-4 grid grid-cols-3 gap-3" style={{ scrollbarWidth: "none" }}>
          {!catalog && <p className="col-span-3 text-center text-sm text-muted-foreground py-6">Yuklanmoqda...</p>}
          {(groups[activeTier] || []).map((g) => {
            const isFreeKind = g.tier === "free";
            const cannotAfford = isFreeKind ? freeRemaining <= 0 : balance < g.price;
            const tier = TIER_META[g.tier];
            return (
              <button
                key={g.kind}
                data-testid={`gift-${g.kind}`}
                onClick={() => send(g)}
                disabled={cannotAfford || sending !== null}
                className={`relative rounded-2xl border p-3 transition flex flex-col items-center gap-1 ${
                  cannotAfford ? "border-border bg-muted/20 opacity-50" : "border-border bg-card hover:-translate-y-1 hover:shadow-lg active:scale-95"
                }`}
              >
                <span className="text-4xl leading-none">{g.emoji}</span>
                <span className="text-[11px] font-medium text-center leading-tight mt-1">{g[labelKey]}</span>
                {isFreeKind ? (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${tier.cls}`}>BEPUL</span>
                ) : (
                  <span className="text-[10px] text-muted-foreground">
                    {g.price >= 1000 ? `${(g.price / 1000).toFixed(g.price >= 10000 ? 0 : 1)}K` : g.price} so'm
                  </span>
                )}
                {sending === g.kind && <span className="absolute inset-0 grid place-items-center bg-card/80 rounded-2xl text-primary text-xs">Yuborilmoqda...</span>}
              </button>
            );
          })}
        </div>

        {/* Bottom tip */}
        <div className="px-4 py-2.5 border-t border-border/40 text-center text-[11px] text-muted-foreground shrink-0">
          💡 Sovg'a qabul qilgan kishi 50% nominal so'mga aylantirib yechishi mumkin
        </div>
      </div>
    </div>
  );
}

import React, { useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { X } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

const GIFTS = [
  { kind: "rose", emoji: "🌹", price: 50, label: "Atirgul" },
  { kind: "box", emoji: "🎁", price: 200, label: "Sovg'a" },
  { kind: "diamond", emoji: "💎", price: 500, label: "Olmos" },
  { kind: "crown", emoji: "👑", price: 1500, label: "Toj" },
];

export default function GiftModal({ targetId, targetName, onClose, onSent }) {
  const { user, t, refresh } = useApp();
  const [sending, setSending] = useState(null);
  if (!targetId) return null;

  const send = async (kind) => {
    setSending(kind);
    try {
      await api.post("/gifts/send", { to_user_id: targetId, gift_kind: kind });
      toast.success(t("send_gift") + " ✓");
      await refresh();
      onSent?.(kind);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || t("insufficient_balance"));
    } finally {
      setSending(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end" data-testid="gift-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-6 pb-8 animate-fade-up">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-heading text-xl font-semibold">{t("send_gift")}</h3>
            {targetName && <p className="text-xs text-muted-foreground">{targetName}</p>}
          </div>
          <button data-testid="gift-modal-close" onClick={onClose} className="p-2 rounded-full hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {GIFTS.map((g) => {
            const disabled = (user?.balance || 0) < g.price;
            return (
              <button
                key={g.kind}
                data-testid={`gift-${g.kind}`}
                onClick={() => send(g.kind)}
                disabled={disabled || sending !== null}
                className={`rounded-3xl border ${disabled ? "border-border bg-muted/30 opacity-60" : "border-border bg-card hover:-translate-y-0.5"} p-4 transition flex flex-col items-center gap-1`}
              >
                <span className="text-4xl">{g.emoji}</span>
                <span className="text-xs font-medium mt-1">{g.label}</span>
                <span className="text-[11px] text-muted-foreground">{g.price.toLocaleString()} so'm</span>
                {sending === g.kind && <span className="text-[10px] text-primary">...</span>}
              </button>
            );
          })}
        </div>
        <div className="mt-4 text-xs text-center text-muted-foreground">
          {t("balance")}: <span className="font-medium text-foreground">{(user?.balance || 0).toLocaleString()} so'm</span>
        </div>
      </div>
    </div>
  );
}

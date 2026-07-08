import React, { useEffect, useState } from "react";
import { notify } from "@/lib/haptics";

// A static emoji in a chat bubble doesn't feel like it was worth 499,000 so'm.
// Since we can't ship custom Lottie/illustration assets from here, the
// "premium" upgrade is real motion: tier-scaled animation built entirely from
// CSS (no external asset dependency, stays lightweight for the Mini App).
export function tierFromPrice(price) {
  if (price >= 199000) return "luxury";
  if (price >= 25000) return "love";
  if (price > 0) return "care";
  return "free";
}

const PARTICLE_COUNT = { luxury: 14, love: 6, care: 0, free: 0 };

export default function GiftCelebration({ gift, onDone }) {
  const [visible, setVisible] = useState(true);
  const tier = gift?.tier || "care";
  const durationMs = tier === "luxury" ? 2600 : tier === "love" ? 1900 : 1300;

  useEffect(() => {
    if (!gift) return;
    setVisible(true);
    notify("success");
    const t = setTimeout(() => {
      setVisible(false);
      onDone?.();
    }, durationMs);
    return () => clearTimeout(t);
  }, [gift, durationMs, onDone]);

  if (!gift || !visible) return null;

  const particles = Array.from({ length: PARTICLE_COUNT[tier] || 0 });
  const isBig = tier === "luxury" || tier === "love";

  return (
    <div
      className={`fixed inset-0 z-[10002] flex items-center justify-center pointer-events-none ${isBig ? "bg-ink/10" : ""}`}
      data-testid="gift-celebration"
      data-tier={tier}
    >
      <div className="relative flex flex-col items-center gap-2">
        {particles.map((_, i) => (
          <span
            key={i}
            className="gift-particle"
            style={{
              "--angle": `${(360 / particles.length) * i}deg`,
              "--delay": `${(i % 5) * 0.06}s`,
            }}
          >
            ✨
          </span>
        ))}
        <span
          className={tier === "luxury" ? "gift-emoji-luxury" : tier === "love" ? "gift-emoji-love" : "gift-emoji-care"}
          style={{ fontSize: tier === "luxury" ? 96 : tier === "love" ? 64 : 40 }}
        >
          {gift.emoji}
        </span>
        {isBig && gift.label && (
          <span className="rounded-full bg-card/95 border border-gold/40 px-4 py-1.5 text-sm font-semibold shadow-elevated gift-label-in">
            {gift.label}
          </span>
        )}
      </div>
    </div>
  );
}

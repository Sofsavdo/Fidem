import React from "react";
import { ShieldCheck, Gem, MapPin } from "lucide-react";

export function LocationBadge({ verified }) {
  if (!verified) return null;
  return (
    <span
      data-testid="badge-location"
      className="inline-flex items-center gap-1 rounded-full bg-secondary/10 text-secondary border border-secondary/25 px-2 py-0.5 text-[10px] font-medium tracking-wide"
    >
      <MapPin className="w-3 h-3" /> Location
    </span>
  );
}

export function VerifiedBadge({ verified }) {
  if (!verified) return null;
  return (
    <span
      data-testid="badge-verified"
      className="inline-flex items-center gap-1 rounded-full bg-secondary/10 text-secondary border border-secondary/20 px-2 py-0.5 text-[10px] font-medium tracking-wide"
    >
      <ShieldCheck className="w-3 h-3" /> Verified
    </span>
  );
}

export function FinancialBadge({ verified }) {
  if (!verified) return null;
  return (
    <span
      data-testid="badge-financial"
      className="inline-flex items-center gap-1 rounded-full bg-gold-light text-yellow-800 border border-gold/40 px-2 py-0.5 text-[10px] font-medium tracking-wide"
    >
      <Gem className="w-3 h-3" /> Financial
    </span>
  );
}

export function MatchBadge({ score }) {
  let bg = "bg-muted text-muted-foreground";
  if (score >= 80) bg = "bg-secondary text-white";
  else if (score >= 60) bg = "bg-gold text-ink";
  else if (score >= 40) bg = "bg-primary/15 text-primary";
  return (
    <span
      data-testid="match-score"
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${bg}`}
    >
      {score}%
    </span>
  );
}

export function OnlineDot({ online }) {
  if (!online) return null;
  return (
    <span
      data-testid="online-dot"
      className="inline-block w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white"
      title="Online"
    />
  );
}

export function PlanPill({ plan }) {
  if (plan === "vip")
    return (
      <span className="rounded-full px-2 py-0.5 text-[10px] bg-ink text-gold border border-gold/30 font-medium">
        VIP 👑
      </span>
    );
  if (plan === "premium")
    return (
      <span className="rounded-full px-2 py-0.5 text-[10px] bg-gold-light text-yellow-900 border border-gold/40 font-medium">
        Premium 💎
      </span>
    );
  return null;
}

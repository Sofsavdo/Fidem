import React from "react";

// ─────────────────────────────────────────────────────────────────────────
// FIDEM shared UI kit — small, reusable premium primitives so every page
// reads as one product. Keep these lean and composable.
// ─────────────────────────────────────────────────────────────────────────

/** Page title + optional subtitle, consistent across pages. */
export function PageHead({ title, subtitle, right, className = "" }) {
  return (
    <div className={`flex items-start justify-between gap-3 ${className}`}>
      <div className="min-w-0">
        <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

/** Small uppercase section label. */
export function SectionLabel({ children, className = "" }) {
  return <p className={`text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground ${className}`}>{children}</p>;
}

/** Pill segmented control. options=[{key,label}], value, onChange. */
export function Segmented({ options, value, onChange, className = "" }) {
  return (
    <div className={`inline-flex p-1 rounded-2xl bg-muted/60 border border-border/70 w-full ${className}`} role="tablist">
      {options.map((o) => {
        const active = o.key === value;
        return (
          <button
            key={o.key}
            role="tab"
            aria-selected={active}
            data-testid={`seg-${o.key}`}
            onClick={() => onChange(o.key)}
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-colors ${
              active ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/** Formatted price with currency, tabular figures. */
export function Price({ amount, currency = "so'm", className = "", size = "base" }) {
  const sz = size === "lg" ? "text-2xl" : size === "sm" ? "text-sm" : "text-lg";
  return (
    <span className={`font-heading font-semibold tabular-nums ${sz} ${className}`}>
      {Number(amount || 0).toLocaleString()} <span className="text-[0.7em] font-medium opacity-70">{currency}</span>
    </span>
  );
}

/** A compact stat tile. */
export function StatTile({ label, value, sub, tone = "default" }) {
  const tones = {
    default: "bg-card border-border",
    gold: "bg-gold-light/40 border-gold/30",
    secondary: "bg-secondary/8 border-secondary/25",
  };
  return (
    <div className={`rounded-2xl border p-3 ${tones[tone] || tones.default}`}>
      <p className="font-heading text-xl font-semibold tabular-nums leading-tight">{value}</p>
      <p className="text-[11px] text-muted-foreground mt-0.5">{label}</p>
      {sub && <p className="text-[11px] text-secondary mt-0.5">{sub}</p>}
    </div>
  );
}

/** Empty state with icon, message, optional action. */
export function EmptyState({ icon, title, hint, action, className = "" }) {
  return (
    <div className={`text-center py-12 px-6 ${className}`} data-testid="empty-state">
      {icon && <div className="w-14 h-14 mx-auto rounded-2xl bg-muted grid place-items-center text-muted-foreground mb-3">{icon}</div>}
      <p className="font-medium text-foreground">{title}</p>
      {hint && <p className="text-sm text-muted-foreground mt-1 max-w-xs mx-auto">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/** Simple skeleton block. */
export function Skeleton({ className = "" }) {
  return <div className={`bg-muted rounded-2xl animate-pulse ${className}`} />;
}

/** Grid of card skeletons for candidate/saved lists. */
export function CardGridSkeleton({ count = 6, aspect = "aspect-[4/5]" }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className={`${aspect} rounded-3xl`} />
      ))}
    </div>
  );
}

/** Primary gradient CTA button (uses the .btn-primary system). */
export function CTA({ children, className = "", variant = "primary", ...props }) {
  const base = variant === "secondary" ? "btn-secondary" : variant === "ghost"
    ? "w-full rounded-2xl border border-border py-3 font-medium hover:bg-muted transition"
    : "btn-primary";
  return (
    <button className={`${base} ${className}`} {...props}>
      {children}
    </button>
  );
}

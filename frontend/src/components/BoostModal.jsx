import React from "react";
import { Link } from "react-router-dom";
import { X, Rocket, Check, Clock } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { useBoostStatus, useActivateBoost, useBoostAnalytics } from "@/hooks/queries";
import { toast } from "sonner";

function hoursLeft(untilIso) {
  if (!untilIso) return 0;
  const ms = new Date(untilIso).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / (60 * 60 * 1000)));
}

export default function BoostModal({ onClose }) {
  const { t, user } = useApp();
  const { data: status } = useBoostStatus();
  const activate = useActivateBoost();
  const { data: analytics } = useBoostAnalytics(!!status?.active);
  const m = analytics?.boost;

  const price = status?.price ?? 5000;
  const balance = user?.balance || 0;
  const canAfford = balance >= price;

  const activateNow = () => {
    // Optimistic: the mutation already flips `active` in cache on tap, so the
    // modal reflects success immediately — the network call reconciles after.
    activate.mutate(undefined, {
      onSuccess: () => toast.success(t("profile_boost_title") + " 🚀"),
      onError: (e) => toast.error(e?.response?.data?.detail || t("error_generic")),
    });
  };

  return (
    <div className="fixed inset-0 flex items-end sm:items-center sm:justify-center" style={{ zIndex: 10001 }} data-testid="boost-modal">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="relative w-full sm:max-w-md bg-card rounded-t-3xl sm:rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto"
        style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
      >
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-heading text-xl font-semibold flex items-center gap-2">
            <Rocket className="w-5 h-5 text-primary" /> {t("profile_boost_title")}
          </h3>
          <button data-testid="boost-modal-close" onClick={onClose} className="p-2 -m-2 rounded-full hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{t("profile_boost_desc")}</p>

        <ul className="mt-4 space-y-2">
          {[t("bullet_top_feed"), t("bullet_views_3_5x"), t("bullet_faster_messages")].map((b, i) => (
            <li key={i} className="text-sm flex items-center gap-2">
              <Check className="w-4 h-4 text-secondary shrink-0" /> {b}
            </li>
          ))}
        </ul>

        {status?.active ? (
          <div className="mt-5 space-y-3" data-testid="boost-active-state">
            <div className="rounded-2xl bg-secondary/10 border border-secondary/30 p-4 flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-secondary shrink-0" />
              <span>🚀 {t("profile_boost_title")} — {t("boost_time_left").replace("{n}", hoursLeft(status.until))}</span>
            </div>
            {/* Show what the paid boost is actually delivering — proves the value */}
            <div data-testid="boost-results">
              <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">{t("boost_results_title")}</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["impressions", t("boost_metric_impressions")],
                  ["views", t("boost_metric_views")],
                  ["likes", t("boost_metric_likes")],
                  ["messages", t("boost_metric_messages")],
                ].map(([k, label]) => (
                  <div key={k} className="rounded-xl bg-card border border-border p-3">
                    <p className="font-heading text-xl font-semibold tabular-nums">{(m?.[k] ?? 0).toLocaleString()}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-5 space-y-2">
            <p className="text-xs text-muted-foreground" data-testid="boost-inactive-state">{t("no_active_boost")}</p>
            <button
              data-testid="boost-activate"
              onClick={activateNow}
              disabled={!canAfford || activate.isPending}
              className="w-full rounded-2xl bg-primary text-white py-3 font-medium disabled:opacity-50 inline-flex items-center justify-center gap-2"
            >
              🚀 {t("activate_with_balance")} · {price.toLocaleString()} {t("sum")}
            </button>
            {!canAfford && (
              <Link
                to="/premium?tab=balance"
                data-testid="boost-topup-link"
                onClick={onClose}
                className="block text-center text-xs text-primary font-medium py-1"
              >
                {t("topup_balance")} ({balance.toLocaleString()} {t("sum")}) →
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

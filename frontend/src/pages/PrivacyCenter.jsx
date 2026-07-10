import React from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, EyeOff, Eye, Check, Lock, Crown } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

// Privacy center: opened from Me for non-VIP users (VIP toggles inline on
// Me). Each tier gets its OWN row with its own working control or a clear
// "this needs plan X" button — no dead toggles, no wall of text on Me.
export default function PrivacyCenter() {
  const { t, user, refresh } = useApp();

  const privacyMutation = useMutation({
    mutationFn: (patch) => api.post("/settings/privacy", patch),
    onSuccess: () => refresh(),
    onError: (e) => {
      const detail = (e?.response?.data?.detail || "").toString();
      if (detail === "privacy_boost_active") toast.error(t("privacy_boost_active"));
      else if (detail === "privacy_requires_plan") toast.error(t("privacy_requires_plan"));
      else toast.error(t("error_generic"));
    },
  });

  if (!user) return null;
  const plan = user.plan || "free";
  const isPaid = ["standard", "premium", "vip"].includes(plan);
  const hasIncognito = ["premium", "vip"].includes(plan);
  const isVip = plan === "vip";

  const Tier = ({ name, price, included, children, control }) => (
    <div className={`rounded-3xl border p-4 ${included ? "bg-card border-secondary/40" : "bg-card border-border"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold flex items-center gap-1.5">
            {included ? <Check className="w-4 h-4 text-secondary" /> : <Lock className="w-4 h-4 text-muted-foreground" />}
            {name} <span className="text-[11px] font-normal text-muted-foreground">· {price.toLocaleString()} {t("sum")}{t("plan_per_month")}</span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{children}</p>
        </div>
      </div>
      <div className="mt-3">{control}</div>
    </div>
  );

  const upgradeBtn = (hl, label) => (
    <Link
      to={`/premium?tab=plans&hl=${hl}`}
      data-testid={`privacy-upgrade-${hl}`}
      className="flex items-center justify-center gap-1.5 rounded-2xl bg-primary/10 border border-primary/25 px-4 py-2.5 text-sm font-semibold text-primary active:scale-[0.98] transition"
    >
      {label} <ChevronRight className="w-4 h-4" />
    </Link>
  );

  return (
    <div>
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="privacycenter-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-semibold text-lg flex items-center gap-2"><EyeOff className="w-4 h-4" /> {t("hidden_profile_label")}</span>
      </header>

      <div className="max-w-2xl mx-auto p-4 md:p-6 space-y-4" data-testid="privacy-center">
        <p className="text-sm text-muted-foreground leading-relaxed">{t("privacy_center_intro")}</p>

        {/* Tier 1 — Standard: invisibility (the actual hidden-mode switch) */}
        <Tier
          name="Standard"
          price={34900}
          included={isPaid}
          control={
            isPaid ? (
              <button
                type="button"
                data-testid="pc-toggle-hidden"
                disabled={privacyMutation.isPending}
                onClick={() => privacyMutation.mutate({ hidden_profile: !user.hidden_profile })}
                className={`w-full rounded-2xl py-2.5 text-sm font-semibold transition disabled:opacity-50 ${
                  user.hidden_profile ? "bg-secondary text-white" : "bg-muted"
                }`}
              >
                {user.hidden_profile ? `✓ ${t("privacy_on_state")}` : t("privacy_turn_on")}
              </button>
            ) : (
              upgradeBtn("standard", t("privacy_get_standard"))
            )
          }
        >
          {t("privacy_tier_standard")}
        </Tier>

        {/* Tier 2 — Premium: incognito viewing */}
        <Tier
          name="Premium"
          price={79000}
          included={hasIncognito}
          control={
            hasIncognito ? (
              <p className="text-xs text-secondary font-medium flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5" /> {user.hidden_profile ? t("privacy_incognito_on") : t("privacy_incognito_needs_hidden")}
              </p>
            ) : (
              upgradeBtn("premium", t("privacy_get_premium"))
            )
          }
        >
          {t("privacy_tier_premium")}
        </Tier>

        {/* Tier 3 — VIP: photo peek */}
        <Tier
          name="VIP"
          price={199000}
          included={isVip}
          control={
            isVip ? (
              <p className="text-xs text-secondary font-medium flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5" /> {t("privacy_peek_included")}
              </p>
            ) : (
              upgradeBtn("vip", t("privacy_get_vip"))
            )
          }
        >
          {t("privacy_tier_vip")}
        </Tier>

        {/* Full-privacy CTA */}
        {!isVip && (
          <Link
            to="/premium?tab=plans&hl=vip"
            data-testid="privacy-full-vip-cta"
            className="flex items-center justify-between gap-3 rounded-3xl bg-gradient-to-r from-ink to-zinc-800 text-white p-4 active:scale-[0.98] transition"
          >
            <div className="min-w-0">
              <p className="font-heading text-base font-semibold flex items-center gap-1.5"><Crown className="w-4 h-4 text-gold" /> {t("privacy_full_title")}</p>
              <p className="text-xs text-white/70 mt-0.5">{t("privacy_full_hint")}</p>
            </div>
            <span className="shrink-0 rounded-full bg-white text-ink text-xs font-semibold px-3.5 py-2">VIP →</span>
          </Link>
        )}
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { VerifiedBadge, FinancialBadge, PlanPill } from "@/components/Badges";
import PhotoUpload from "@/components/PhotoUpload";
import { photoSrc } from "@/lib/photo";
import { purchasePlan } from "@/lib/purchase";
import { ChevronRight, Crown, Wallet, Share2, Settings as SettingsIcon, LogOut, ShieldCheck, Clock, SlidersHorizontal, Brain, BookOpen, Phone, Trophy, Rocket, MessageCircle, EyeOff, Camera } from "lucide-react";
import BoostModal from "@/components/BoostModal";
import LocationVerifyCard from "@/components/LocationVerifyCard";
import { toast } from "sonner";
import { useReferral, useSavedSummary, useLeaderboard, QK } from "@/hooks/queries";
import { useQueryClient, useMutation } from "@tanstack/react-query";

// Static support contact - a real Telegram account admins actually monitor,
// not the bot (which only understands the mini-app commands).
const ADMIN_TELEGRAM_USERNAME = process.env.REACT_APP_ADMIN_TELEGRAM_USERNAME || "FidemAppSupport";

// Inside the Telegram Mini App webview a plain target=_blank anchor to t.me
// is silently swallowed - Telegram links must go through openTelegramLink.
function openSupportChat() {
  const url = `https://t.me/${ADMIN_TELEGRAM_USERNAME}`;
  const tg = window.Telegram?.WebApp;
  if (tg?.openTelegramLink) {
    try { tg.openTelegramLink(url); return; } catch { /* fall through */ }
  }
  window.open(url, "_blank", "noopener");
}

export default function Me() {
  const { user, t, logout, refresh, wsEvent } = useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [boostOpen, setBoostOpen] = useState(false);

  const { data: referral } = useReferral();
  const { data: interestedSummary } = useSavedSummary();
  const { data: leaders = [] } = useLeaderboard("all");
  const myRank = leaders.findIndex((row) => row.user?.id === user?.id);

  // Invalidate notifications on WS event so the top-bar count stays in sync
  useEffect(() => {
    if (wsEvent?.type === "notification") {
      queryClient.invalidateQueries({ queryKey: QK.notifications });
    }
  }, [wsEvent, queryClient]);

  // Privacy toggles (photo open to everyone / hidden profile). The backend
  // refuses hidden_profile=true while a paid boost is running
  // ("privacy_boost_active") - surface that as a clear message, not a
  // generic error.
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

  const isPaidPlan = ["standard", "premium", "vip"].includes(user.plan);

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-5">
      {/* Header — notifications & language live in the top bar, so they're not
          duplicated here. */}
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">{t("me")}</h1>
      </div>

      {/* Loud reminder when hidden mode is on — people forget they enabled it,
          then wonder why nobody writes (and try to buy a boost, which the
          backend rightly refuses). */}
      {user.hidden_profile && (
        <div
          data-testid="hidden-profile-banner"
          className="rounded-3xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 p-4 flex items-start gap-3"
        >
          <EyeOff className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">{t("hidden_profile_active_banner")}</p>
        </div>
      )}

      {/* Profile card — single tappable photo (avatar), no duplicate upload block */}
      <div className="rounded-3xl bg-card border border-border p-4 shadow-soft" data-testid="me-profile-card">
        <div className="flex items-center gap-4">
          <PhotoUpload
            avatar
            name={user.name}
            value={user.photo_url}
            onChange={async (url) => {
              await api.patch("/profile", { photo_url: url });
              await refresh();
            }}
            testid="me-photo-upload"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium text-lg truncate">{user.name}, {user.age}</p>
              <PlanPill plan={user.plan} />
              {user.plan !== "free" && user.plan_until && (() => {
                const daysLeft = Math.max(0, Math.ceil((new Date(user.plan_until) - Date.now()) / 86400000));
                return (
                  <button
                    type="button"
                    onClick={() => purchasePlan(user.plan, { t, navigate, onPaid: refresh })}
                    data-testid="plan-days-left"
                    className={`text-[10px] px-2 py-0.5 rounded-full border ${daysLeft <= 3 ? "bg-amber-50 text-amber-700 border-amber-300" : "bg-muted text-muted-foreground border-border"}`}
                  >
                    {daysLeft} {t("days_left_short")}
                  </button>
                );
              })()}
            </div>
            <p className="text-xs text-muted-foreground truncate">{user.region} · {user.profession || "—"}</p>
            <div className="flex gap-1 mt-1.5 flex-wrap">
              <VerifiedBadge verified={user.verified_selfie} />
              <FinancialBadge verified={user.verified_financial} />
              {user.verified_identity && (
                <span className="inline-flex items-center gap-1 rounded-full bg-secondary/10 text-secondary border border-secondary/25 px-2 py-0.5 text-[10px]">
                  <ShieldCheck className="w-3 h-3" /> ID
                </span>
              )}
            </div>
          </div>
        </div>
        {user.avg_response_min != null && (
          <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 text-xs text-muted-foreground" data-testid="me-response-speed">
            <Clock className="w-3.5 h-3.5" />
            {t("response_usually")} <strong className="text-foreground">{user.avg_response_min < 60 ? `${user.avg_response_min} ${t("minutes")}` : `${Math.round(user.avg_response_min / 60)} ${t("hours")}`}</strong>
          </div>
        )}
      </div>

      {/* Contextual upsell — just a teaser + count here (Me is the profile
          settings page, not a place to browse dozens of masked profiles).
          Tapping goes to the dedicated Saved > Interested page, which shows
          the actual list and the plan upsell in full. */}
      {/* While the summary is loading, hold the slot with an equal-height
          skeleton so the page doesn't jump when the banner pops in — the
          "Me titraydi" bug was blocks mounting late and pushing everything
          below them down. Collapses only for users with zero interest. */}
      {!["premium", "vip"].includes(user.plan) && interestedSummary === undefined && (
        <div className="rounded-3xl bg-card border border-border p-4 animate-pulse" aria-hidden="true">
          <div className="h-5 w-2/3 rounded bg-muted" />
        </div>
      )}
      {!["premium", "vip"].includes(user.plan) && interestedSummary?.total > 0 && (
        <Link
          to="/saved?tab=interested"
          data-testid="profile-teaser-banner"
          className="block rounded-3xl bg-gradient-to-r from-primary/15 via-primary/5 to-card border border-primary/30 p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform"
        >
          {/* Stacked layout: avatars+text on top, CTA full-width below — a
              single horizontal row here squeezed the avatar stack, title,
              subtitle and button all into too little space. */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              {/* Masked avatar stack — real (locked) people, not just a line of
                  text nobody reads. Photos are hidden for free users, so each
                  circle shows the masked initial on a warm gradient. */}
              <div className="flex -space-x-3 shrink-0">
                {(interestedSummary.items || []).slice(0, 3).map((p, i) => (
                  <div
                    key={p.id || i}
                    className="w-11 h-11 rounded-full ring-2 ring-card grid place-items-center font-heading font-semibold text-white text-sm bg-gradient-to-br from-primary to-rose-400 overflow-hidden"
                    style={{ zIndex: 3 - i }}
                  >
                    {p.photo_url ? (
                      <img src={photoSrc(p.photo_url)} alt="" className="w-full h-full object-cover" />
                    ) : (
                      (p.name || "?")[0]
                    )}
                  </div>
                ))}
                {interestedSummary.total > 3 && (
                  <div className="w-11 h-11 rounded-full ring-2 ring-card grid place-items-center bg-ink text-white text-xs font-bold" style={{ zIndex: 0 }}>
                    +{interestedSummary.total - 3}
                  </div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold leading-snug">💘 {t("profile_teaser_title")}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{t("profile_teaser_subtitle").replace("{n}", interestedSummary.total)}</p>
              </div>
            </div>
            <span className="block text-center rounded-full bg-primary text-white text-xs font-semibold px-3.5 py-2.5">{t("profile_teaser_cta")}</span>
          </div>
        </Link>
      )}

      {/* Location verification (Map M1) */}
      <LocationVerifyCard />

      {/* Completeness — with a direct CTA to finish the missing parts */}
      <div className="rounded-3xl bg-card border border-border p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("completeness")}</p>
          <p className="text-sm font-semibold" data-testid="me-completeness">{user.completeness || 0}%</p>
        </div>
        <div className="h-2 rounded-full bg-border overflow-hidden">
          <div
            className={`h-full transition-all ${user.completeness === 100 ? "bg-gold" : "bg-primary"}`}
            style={{ width: `${user.completeness || 0}%` }}
          />
        </div>
        {(user.completeness || 0) < 100 && (
          <Link
            to="/onboarding?edit=1"
            data-testid="me-complete-profile"
            className="mt-3 flex items-center justify-between rounded-2xl bg-primary/8 border border-primary/25 px-4 py-2.5 active:scale-[0.99] transition"
          >
            <span className="text-sm font-medium text-primary">{t("complete_profile_cta")}</span>
            <ChevronRight className="w-4 h-4 text-primary" />
          </Link>
        )}

        {/* Privacy: open photo + hidden profile, right where people look at
            their own profile state. */}
        <div className="mt-4 pt-4 border-t border-border space-y-4">
          <PrivacyToggle
            testid="toggle-photo-public"
            icon={<Camera className="w-4 h-4" />}
            label={t("photo_public_label")}
            hint={t("photo_public_hint")}
            checked={!!user.photo_public}
            disabled={privacyMutation.isPending}
            onChange={(v) => privacyMutation.mutate({ photo_public: v })}
          />
          {user.plan === "vip" ? (
            // VIP: full privacy is theirs — the switch works right here.
            <PrivacyToggle
              testid="toggle-hidden-profile"
              icon={<EyeOff className="w-4 h-4" />}
              label={t("hidden_profile_label")}
              hint={t("hidden_profile_hint")}
              checked={!!user.hidden_profile}
              disabled={privacyMutation.isPending}
              onChange={(v) => privacyMutation.mutate({ hidden_profile: v })}
            />
          ) : (
            // Everyone else: a live row (never a dead toggle) that opens the
            // privacy center where each tier has its own working control.
            <Link
              to="/privacy-center"
              data-testid="open-privacy-center"
              className="flex items-start justify-between gap-3 active:scale-[0.99] transition"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <span className="text-muted-foreground mt-0.5 shrink-0"><EyeOff className="w-4 h-4" /></span>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{t("hidden_profile_label")}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
                    {user.hidden_profile ? `✓ ${t("privacy_on_state")}` : t("privacy_paid_hint")}
                  </p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
            </Link>
          )}
        </div>
      </div>

      {/* Rankings teaser — replaces the old badges/achievements card, which
          had no real effect on the user. This one is concrete: your actual
          standing, the current #1, and a direct path to climb it. */}
      <Link to="/rankings" data-testid="rankings-teaser" className="block rounded-3xl bg-gradient-to-br from-gold/12 via-card to-secondary/10 border border-gold/25 p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-2xl bg-gold/15 text-gold-dark grid place-items-center shrink-0">
              <Trophy className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <p className="font-heading font-semibold">{t("top_supporters")}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {myRank >= 0 ? `${t("rank_your_rank")}: #${myRank + 1}` : (leaders[0]?.user?.name ? `#1 · ${leaders[0].user.name}` : t("rank_boost_hint"))}
              </p>
            </div>
          </div>
          <span className="shrink-0 text-xs font-semibold text-gold-dark whitespace-nowrap">{t("rank_boost_cta")} →</span>
        </div>
      </Link>

      {/* Premium/balance row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Link to="/premium?tab=plans" data-testid="link-premium" className="rounded-3xl bg-gradient-to-br from-ink to-zinc-800 text-white p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform">
          <Crown className="w-5 h-5 text-gold" />
          <p className="font-heading text-lg mt-2">{t("premium")}</p>
          <p className="text-xs text-white/70 mt-0.5">{t("premium_subtitle")} →</p>
        </Link>
        <Link to="/premium?tab=balance" data-testid="link-balance" className="rounded-3xl bg-card border border-border p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform">
          <Wallet className="w-5 h-5 text-secondary" />
          <p className="font-heading text-lg mt-2">{(user.balance || 0).toLocaleString()} {t("sum")}</p>
          <p className="text-xs text-secondary mt-0.5">{t("app_balance_title")} →</p>
        </Link>
        <button
          type="button"
          onClick={() => setBoostOpen(true)}
          data-testid="link-boost"
          className="text-left rounded-3xl bg-gradient-to-br from-primary/12 to-card border border-primary/30 p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform col-span-2 md:col-span-1"
        >
          <div className="flex items-center justify-between">
            <Rocket className="w-5 h-5 text-primary" />
            <span className="text-[10px] font-semibold text-primary bg-primary/10 rounded-full px-2 py-0.5">{t("bullet_views_3_5x")}</span>
          </div>
          <p className="font-heading text-lg mt-2">{t("boost_title")}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t("boost_me_hint")} →</p>
        </button>
      </div>
      {boostOpen && <BoostModal onClose={() => setBoostOpen(false)} />}

      {/* Daily streak lives in Sozlamalar (/me/settings) now — Me stays a
          clean overview page. */}

      {/* Invite friends → unified single entrypoint. The card frame renders
          immediately (every user has referral data) with skeleton text while
          it loads — mounting it late made the whole page below jump. */}
      <Link to="/referral" data-testid="invite-card" className="block rounded-3xl bg-gradient-to-r from-secondary/10 to-card border border-secondary/30 p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="font-heading text-lg flex items-center gap-2"><Share2 className="w-4 h-4 text-secondary" /> {t("invite_friends")}</p>
            {/* Always-visible value prop - a first-time viewer with 0/0 stats
                otherwise has no way to learn this pays real money at all,
                since the raw invite/paid counters below mean nothing until
                you already know what they represent. */}
            <p className="text-xs font-medium text-secondary mt-0.5">{t("invite_friends_earn_hint")}</p>
            {referral ? (
              <>
                <p className="text-xs text-muted-foreground mt-0.5">{referral.invited_count || 0} {t("ref_invites")} · {referral.paid_referrals || 0} {t("ref_paid_referrals")}</p>
                {referral.monthly_tier && (
                  <p className="text-xs text-secondary mt-0.5">{t("monthly_tier")}: {referral.monthly_tier} ({referral.monthly_count || 0}/{referral.next_tier_threshold || 300})</p>
                )}
              </>
            ) : (
              <div className="h-3.5 w-40 rounded bg-muted animate-pulse mt-1.5" aria-hidden="true" />
            )}
          </div>
          <span className="text-secondary font-medium shrink-0">{t("share")} →</span>
        </div>
      </Link>

      {/* Profil */}
      <div>
        <p className="field-label mb-2 px-1">{t("me_group_profile")}</p>
        <div className="rounded-3xl bg-card border border-border divide-y">
          <NavRow to="/personality" testid="link-personality" icon={<Brain className="w-4 h-4 text-secondary" />} label={t("personality_test")} />
          <NavRow to="/family" testid="link-family" icon={<Phone className="w-4 h-4 text-foreground" />} label={t("family_contact")} />
          <NavRow to="/verification" testid="link-verification" icon={<ShieldCheck className="w-4 h-4 text-foreground" />} label={t("profile_verification")} />
        </div>
      </div>

      {/* Pul va imkoniyatlar */}
      <div>
        <p className="field-label mb-2 px-1">{t("me_group_money")}</p>
        <div className="rounded-3xl bg-card border border-border divide-y">
          <NavRow to="/concierge" testid="link-concierge" icon={<Crown className="w-4 h-4 text-secondary" />} label={`${t("concierge_title")} (199,000 ${t("sum")})`} />
          <NavRow to="/withdrawals" testid="link-withdrawals" icon={<Wallet className="w-4 h-4 text-foreground" />} label={`${t("withdraw_money")} (${(user.withdrawable_balance || 0).toLocaleString()} ${t("sum")})`} />
        </div>
      </div>

      {/* Ilova */}
      <div>
        <p className="field-label mb-2 px-1">{t("me_group_app")}</p>
        <div className="rounded-3xl bg-card border border-border divide-y">
          <NavRow to="/stories" testid="link-stories" icon={<BookOpen className="w-4 h-4 text-foreground" />} label={t("success_stories")} />
          <NavRow to="/me/settings" testid="link-settings" icon={<SlidersHorizontal className="w-4 h-4" />} label={t("me_settings_title")} />
          {user.is_admin && (
            <NavRow to="/admin" testid="link-admin" icon={<SettingsIcon className="w-4 h-4" />} label={t("admin_panel")} />
          )}
          <button
            type="button"
            onClick={openSupportChat}
            data-testid="link-contact-admin"
            className="flex items-center justify-between p-4 w-full text-left"
          >
            <span className="flex items-center gap-3 text-sm"><MessageCircle className="w-4 h-4 text-secondary" /> {t("contact_admin")}</span>
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </button>
          <button data-testid="btn-logout" onClick={logout} className="flex items-center justify-between p-4 w-full text-left">
            <span className="flex items-center gap-3 text-sm text-foreground"><LogOut className="w-4 h-4" /> {t("logout")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

const NavRow = React.memo(function NavRow({ to, testid, icon, label }) {
  return (
    <Link to={to} data-testid={testid} className="flex items-center justify-between p-4">
      <span className="flex items-center gap-3 text-sm">{icon} {label}</span>
      <ChevronRight className="w-4 h-4 text-muted-foreground" />
    </Link>
  );
});

function PrivacyToggle({ testid, icon, label, hint, checked, disabled, onChange }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-start gap-2.5 min-w-0">
        <span className="text-muted-foreground mt-0.5 shrink-0">{icon}</span>
        <div className="min-w-0">
          <p className="text-sm font-medium">{label}</p>
          <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{hint}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        data-testid={testid}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative shrink-0 w-11 h-6 rounded-full transition-colors disabled:opacity-50 ${checked ? "bg-primary" : "bg-border"}`}
      >
        <span
          className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${checked ? "left-[calc(100%-1.375rem)]" : "left-0.5"}`}
        />
      </button>
    </div>
  );
}

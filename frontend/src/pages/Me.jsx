import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { VerifiedBadge, FinancialBadge, PlanPill } from "@/components/Badges";
import PhotoUpload from "@/components/PhotoUpload";
import { ChevronRight, Crown, Gem, Wallet, Share2, Settings as SettingsIcon, LogOut, Copy, Trophy, ShieldCheck, Bell, Clock, SlidersHorizontal, Brain, UsersRound, Pen, BookOpen, Phone, Plane, TrendingUp, Award, Rocket } from "lucide-react";
import ProgressCard from "@/components/ProgressCard";
import LangSwitch from "@/components/LangSwitch";
import BoostModal from "@/components/BoostModal";
import { photoSrc } from "@/lib/photo";
import { toast } from "sonner";
import { useReferral, useNotifications, useDailyStatus, useRankings, useSaved, QK } from "@/hooks/queries";
import { useQueryClient, useMutation } from "@tanstack/react-query";

export default function Me() {
  const { user, t, logout, refresh, wsEvent } = useApp();
  const queryClient = useQueryClient();
  const [leadPeriod, setLeadPeriod] = useState("all");
  const [boostOpen, setBoostOpen] = useState(false);

  const { data: referral } = useReferral();
  const { data: notifications = [] } = useNotifications();
  const { data: daily, refetch: refetchDaily } = useDailyStatus();
  const { data: leaders = [] } = useRankings("global");
  const { data: profileViewers = [] } = useSaved("viewers");
  const { data: profileSavers = [] } = useSaved("by_others");

  const unread = notifications.filter((x) => !x.read).length;

  // Invalidate notifications on WS event so count stays in sync
  useEffect(() => {
    if (wsEvent?.type === "notification") {
      queryClient.invalidateQueries({ queryKey: QK.notifications });
    }
  }, [wsEvent, queryClient]);

  const claimDailyMutation = useMutation({
    mutationFn: () => api.post("/daily/claim"),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: QK.dailyStatus });
      const previous = queryClient.getQueryData(QK.dailyStatus);
      queryClient.setQueryData(QK.dailyStatus, (old) => old ? { ...old, claimed_today: true } : old);
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(QK.dailyStatus, context.previous);
    },
    onSuccess: (r) => {
      toast.success(`+${r.data.bonus} ${r.data.currency === "coins" ? t("coin") : t("sum")}`);
      queryClient.invalidateQueries({ queryKey: QK.dailyStatus });
      refresh();
    },
  });

  if (!user) return null;

  const copy = (txt) => {
    navigator.clipboard.writeText(txt).then(() => toast.success(t("copied")));
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">{t("me")}</h1>
        <div className="flex items-center gap-2">
          <Link to="/notifications" data-testid="link-notifications" className="relative p-2 rounded-full hover:bg-muted">
            <Bell className="w-4 h-4" />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-primary text-white text-[9px] font-medium grid place-items-center">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </Link>
          <LangSwitch />
        </div>
      </div>

      {/* Profile card */}
      <div className="rounded-3xl bg-card border border-border p-4 shadow-soft" data-testid="me-profile-card">
        <div className="flex items-center gap-4">
          <div className="relative w-16 h-16 rounded-2xl bg-muted overflow-hidden flex-shrink-0">
            {user.photo_url ? (
              <img loading="lazy" decoding="async" src={photoSrc(user.photo_url)} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full grid place-items-center text-muted-foreground text-xl font-heading">{user.name?.[0]}</div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium text-lg truncate">{user.name}, {user.age}</p>
              <PlanPill plan={user.plan} />
            </div>
            <p className="text-xs text-muted-foreground truncate">{user.region} · {user.profession || "—"}</p>
            <div className="flex gap-1 mt-1.5 flex-wrap">
              <VerifiedBadge verified={user.verified_selfie} />
              <FinancialBadge verified={user.verified_financial} />
              {user.verified_identity && (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 text-[10px]">
                  <ShieldCheck className="w-3 h-3" /> ID
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">{t("photo")}</p>
          <PhotoUpload
            value={user.photo_url}
            onChange={async (url) => {
              await api.patch("/profile", { photo_url: url });
              await refresh();
            }}
            testid="me-photo-upload"
          />
          {user.avg_response_min != null && (
            <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground" data-testid="me-response-speed">
              <Clock className="w-3.5 h-3.5" />
              {t("response_usually")} <strong className="text-foreground">{user.avg_response_min < 60 ? `${user.avg_response_min} ${t("minutes")}` : `${Math.round(user.avg_response_min / 60)} ${t("hours")}`}</strong>
            </div>
          )}
        </div>
      </div>

      {/* Contextual upsell — surfaces existing profile_views/saved-by-others data instead of burying it in a tab */}
      {!["premium", "vip"].includes(user.plan) && (profileViewers.length > 0 || profileSavers.length > 0) && (
        <Link
          to="/premium?tab=plans"
          data-testid="profile-teaser-banner"
          className="block rounded-3xl bg-gradient-to-r from-primary/10 to-card border border-primary/30 p-4 hover:-translate-y-0.5 transition-transform"
        >
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium leading-snug">
              {profileViewers.length > 0 && profileSavers.length > 0
                ? t("profile_teaser_both").replace("{n}", profileViewers.length).replace("{m}", profileSavers.length)
                : profileViewers.length > 0
                ? t("profile_teaser_views_only").replace("{n}", profileViewers.length)
                : t("profile_teaser_saves_only").replace("{m}", profileSavers.length)}
            </p>
            <span className="shrink-0 text-xs font-semibold text-primary whitespace-nowrap">{t("profile_teaser_cta")} →</span>
          </div>
        </Link>
      )}

      {/* Completeness */}
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
      </div>

      {/* Gamification — level + XP + badges */}
      <ProgressCard />

      {/* Premium/balance row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Link to="/premium?tab=plans" data-testid="link-premium" className="rounded-3xl bg-gradient-to-br from-ink to-zinc-800 text-white p-4 hover:-translate-y-0.5 transition-transform">
          <Crown className="w-5 h-5 text-gold" />
          <p className="font-heading text-lg mt-2">{t("premium")}</p>
          <p className="text-xs text-white/70 mt-0.5">{t("premium_subtitle")} →</p>
        </Link>
        <Link to="/withdrawals" data-testid="link-balance" className="rounded-3xl bg-card border border-border p-4 hover:-translate-y-0.5 transition-transform">
          <Wallet className="w-5 h-5 text-foreground" />
          <p className="font-heading text-lg mt-2">{(user.balance || 0).toLocaleString()} {t("sum")}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t("balance")}</p>
        </Link>
        <button
          type="button"
          onClick={() => setBoostOpen(true)}
          data-testid="link-boost"
          className="text-left rounded-3xl bg-gradient-to-br from-primary/10 to-card border border-primary/30 p-4 hover:-translate-y-0.5 transition-transform col-span-2 md:col-span-1"
        >
          <Rocket className="w-5 h-5 text-foreground" />
          <p className="font-heading text-lg mt-2">{t("boost_title")}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t("boost_subtitle")} →</p>
        </button>
      </div>
      {boostOpen && <BoostModal onClose={() => setBoostOpen(false)} />}

      {/* Daily streak */}
      {daily && (
        <div className="rounded-3xl bg-gradient-to-r from-gold/15 to-card border border-gold/30 p-4 flex items-center justify-between" data-testid="daily-strip">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("daily_streak")}</p>
            <p className="font-heading text-2xl">{daily.streak} {t("day_word")} 🔥</p>
          </div>
          {daily.claimed_today ? (
            <span className="text-xs text-secondary">✓ {t("daily")}</span>
          ) : (
            <button
              data-testid="daily-claim-inline"
              onClick={() => claimDailyMutation.mutate()}
              disabled={claimDailyMutation.isPending}
              className="rounded-xl bg-gold text-ink px-4 py-2 text-sm font-medium disabled:opacity-60"
            >
              +{daily.next_bonus} {daily.currency === "coins" ? t("coin") : t("sum")}
            </button>
          )}
        </div>
      )}

      {/* Invite friends → unified single entrypoint */}
      {referral && (
        <Link to="/referral" data-testid="invite-card" className="block rounded-3xl bg-gradient-to-r from-secondary/10 to-card border border-secondary/30 p-4 hover:-translate-y-0.5 transition-transform">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="font-heading text-lg flex items-center gap-2"><Share2 className="w-4 h-4 text-secondary" /> {t("invite_friends")}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{referral.invited_count || 0} {t("ref_invites")} · {referral.paid_referrals || 0} {t("ref_paid_referrals")}</p>
              {referral.monthly_tier && (
                <p className="text-xs text-secondary mt-0.5">{t("monthly_tier")}: {referral.monthly_tier} ({referral.monthly_count || 0}/{referral.next_tier_threshold || 300})</p>
              )}
            </div>
            <span className="text-secondary font-medium">{t("share")} →</span>
          </div>
        </Link>
      )}

      {/* Verification actions — full upload flow on /verification */}
      <div className="rounded-3xl bg-card border border-border divide-y">
        <Row
          icon={<ShieldCheck className="w-4 h-4 text-secondary" />}
          label={t("request_selfie")}
          right={user.verified_selfie ? <span className="text-secondary text-xs">✓</span> : (
            <Link to="/verification" data-testid="req-verify-selfie" className="text-xs text-foreground font-medium">{t("verify_go_page")}</Link>
          )}
        />
        <Row
          icon={<Gem className="w-4 h-4 text-gold-dark" />}
          label={t("financial_verification")}
          right={user.verified_financial ? <span className="text-secondary text-xs">✓</span> : (
            <Link to="/verification" data-testid="req-verify-financial" className="text-xs text-foreground font-medium">{t("verify_go_page")}</Link>
          )}
        />
      </div>

      {/* Leaderboard */}
      <div className="rounded-3xl bg-card border border-border p-4" data-testid="leaderboard-card">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-gold-dark" />
          <p className="font-heading text-lg">{t("top_supporters")}</p>
        </div>
        <div className="flex gap-1 mt-3 mb-3">
          {[
            ["day", t("daily")],
            ["week", t("weekly")],
            ["month", t("monthly")],
            ["all", t("all_time")],
          ].map(([k, l]) => (
            <button
              key={k}
              data-testid={`lead-${k}`}
              onClick={() => setLeadPeriod(k)}
              className={`text-[10px] px-2 py-1 rounded-full border ${
                leadPeriod === k ? "bg-foreground text-background border-foreground" : "bg-card border-border"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {leaders.length === 0 && <p className="text-xs text-muted-foreground">{t("no_data")}</p>}
          {leaders.slice(0, 10).map((row, i) => (
            <div key={row.user_id || row.id || i} className="flex items-center gap-3 text-sm">
              <span className="w-5 text-center font-medium text-muted-foreground">{i + 1}</span>
              <div className="w-7 h-7 rounded-full bg-muted overflow-hidden">
                {row.photo_url && <img loading="lazy" decoding="async" src={photoSrc(row.photo_url)} alt="" className="w-full h-full object-cover" />}
              </div>
              <span className="flex-1 truncate">{row.name || "—"}</span>
              <span className="text-gold-dark font-medium">{(row.ranking_score || row.total || 0).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Profil */}
      <div>
        <p className="field-label mb-2 px-1">{t("me_group_profile")}</p>
        <div className="rounded-3xl bg-card border border-border divide-y">
          <NavRow to="/personality" testid="link-personality" icon={<Brain className="w-4 h-4 text-secondary" />} label={t("personality_test")} />
          <NavRow to="/prompts" testid="link-prompts" icon={<Pen className="w-4 h-4 text-secondary" />} label={t("profile_prompts")} />
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
          <NavRow to="/rankings" testid="link-rankings" icon={<Award className="w-4 h-4 text-gold-dark" />} label={t("rankings")} />
        </div>
      </div>

      {/* Ilova */}
      <div>
        <p className="field-label mb-2 px-1">{t("me_group_app")}</p>
        <div className="rounded-3xl bg-card border border-border divide-y">
          <NavRow to="/stories" testid="link-stories" icon={<BookOpen className="w-4 h-4 text-foreground" />} label={t("success_stories")} />
          <NavRow to="/settings" testid="link-settings" icon={<SlidersHorizontal className="w-4 h-4" />} label={t("who_can_message_me")} />
          {user.is_admin && (
            <NavRow to="/admin" testid="link-admin" icon={<SettingsIcon className="w-4 h-4" />} label={t("admin_panel")} />
          )}
          <button data-testid="btn-logout" onClick={logout} className="flex items-center justify-between p-4 w-full text-left">
            <span className="flex items-center gap-3 text-sm text-foreground"><LogOut className="w-4 h-4" /> {t("logout")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

const Row = React.memo(function Row({ icon, label, right }) {
  return (
    <div className="flex items-center justify-between p-4">
      <span className="flex items-center gap-3 text-sm">{icon} {label}</span>
      <div>{right}</div>
    </div>
  );
});

const NavRow = React.memo(function NavRow({ to, testid, icon, label }) {
  return (
    <Link to={to} data-testid={testid} className="flex items-center justify-between p-4">
      <span className="flex items-center gap-3 text-sm">{icon} {label}</span>
      <ChevronRight className="w-4 h-4 text-muted-foreground" />
    </Link>
  );
});

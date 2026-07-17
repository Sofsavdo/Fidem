import React, { useState, useCallback, useEffect, memo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import posthog from "posthog-js";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { purchasePlan } from "@/lib/purchase";
import { VerifiedBadge, FinancialBadge, MatchBadge, OnlineDot, LocationBadge } from "@/components/Badges";
import CompatibilityCard from "@/components/CompatibilityCard";
import { photoSrc } from "@/lib/photo";
import { formatLastActive } from "@/lib/time";
import { Heart, MessageCircle, ArrowLeft, Lock, Clock, Shield, Share2, Crown, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useCandidateDetail, useSaved, useToggleSave, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { MATCH_EVENT } from "@/components/MatchCelebration";

export default function ProfileDetail() {
  const { id } = useParams();
  const { t, user, refresh } = useApp();
  const nav = useNavigate();
  const queryClient = useQueryClient();
  const [famSending, setFamSending] = useState(false);

  const { data: c, isLoading: loading } = useCandidateDetail(id);
  const { data: savedList = [] } = useSaved("mine");
  const saved = savedList.some((x) => x.id === id);
  const toggleSaveMutation = useToggleSave();
  const saving = toggleSaveMutation.isPending;

  // Contextual upsell: seeing a Premium/VIP profile while on a lower tier is
  // the moment the tier gap is most concrete, so it converts better than a
  // generic banner elsewhere in the app.
  const showTierUpsell = !!c && ["premium", "vip"].includes(c.plan) && !["premium", "vip"].includes(user?.plan);
  useEffect(() => {
    if (showTierUpsell) posthog.capture("profile_tier_upsell_impression", { candidate_id: c?.id, candidate_plan: c?.plan });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showTierUpsell, c?.id]);

  const requestFamily = useCallback(async () => {
    if (user?.plan !== "vip") {
      toast.error(t("family_vip_only"));
      nav("/premium");
      return;
    }
    setFamSending(true);
    try {
      await api.post("/family/request", { target_user_id: id, note: "" });
      toast.success(t("family_request_sent"));
    } catch (e) {
      toast.error(t("error_generic"));
    } finally { setFamSending(false); }
  }, [user?.plan, t, nav, id]);

  const shareProfile = useCallback(async () => {
    const shareText = `${c.name}, ${c.age} — ${c.region}. FIDEM orqali tanishing!`;
    const shareUrl = `https://t.me/${window.Telegram?.WebApp?.initDataUnsafe?.user?.username || 'Fidem_Appbot'}?start=share_${id}`;
    
    if (window.Telegram?.WebApp) {
      try {
        window.Telegram.WebApp.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`);
        toast.success(t("share_success"));
      } catch (e) {
        toast.error(t("error_generic"));
      }
    } else {
      // Fallback for web
      if (navigator.share) {
        try {
          await navigator.share({
            title: `${c.name} — FIDEM`,
            text: shareText,
            url: shareUrl,
          });
        } catch (e) {
          toast.error(t("error_generic"));
        }
      } else {
        // Copy to clipboard
        navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
        toast.success(t("share_copied"));
      }
    }
  }, [c, id, t]);

  const unlockPhoto = useCallback(async () => {
    try {
      const r = await api.post("/photo-unlock/request", { target_user_id: id });
      if (r.data.status === "rejected_wait") {
        toast.error(t("photo_request_rejected_wait"));
        return;
      }
      toast.success(r.data.status === "approved" ? t("photo_unlocked_toast") : t("photo_request_sent_toast"));
      queryClient.invalidateQueries({ queryKey: QK.candidateDetail(id) });
    } catch (e) { toast.error(t("error_generic")); }
  }, [id, t, queryClient]);

  // VIP privacy perk: peek this profile's locked photo once, for 5 seconds.
  // The backend enforces "once per profile"; the timer here just ends the
  // showing — re-requesting returns 409 (peek_used).
  const canPeek = !!user?.hidden_profile && user?.plan === "vip";
  const [peekUrl, setPeekUrl] = useState(null);
  const [peekLeft, setPeekLeft] = useState(0);
  const [peeking, setPeeking] = useState(false);
  useEffect(() => {
    if (!peekUrl) return undefined;
    if (peekLeft <= 0) { setPeekUrl(null); return undefined; }
    const tick = setTimeout(() => setPeekLeft((s) => s - 1), 1000);
    return () => clearTimeout(tick);
  }, [peekUrl, peekLeft]);
  const peekPhoto = useCallback(async () => {
    if (peeking) return;
    setPeeking(true);
    try {
      const r = await api.post(`/photo-peek/${id}`);
      if (r.data?.photo_url) {
        setPeekUrl(r.data.photo_url);
        setPeekLeft(r.data.seconds || 5);
      } else {
        toast.error(t("error_generic"));
      }
    } catch (e) {
      const detail = (e?.response?.data?.detail || "").toString();
      if (detail === "peek_used") toast.error(t("peek_used"));
      else if (detail === "peek_requires_vip") toast.error(t("peek_requires_vip"));
      else toast.error(t("error_generic"));
    } finally {
      setPeeking(false);
    }
  }, [id, peeking, t]);

  const toggleSave = useCallback(() => {
    toggleSaveMutation.mutate(
      { candidate: c, isSaved: saved },
      {
        onSuccess: (data) => {
          if (saved) return;
          if (data?.mutual_match) {
            window.dispatchEvent(new CustomEvent(MATCH_EVENT, { detail: c }));
          } else {
            toast.success(t("liked_toast"), { id: "like" });
          }
        },
      }
    );
  }, [saved, c, t, toggleSaveMutation]);

  if (loading || !c) {
    return (
      <div className="pb-8" data-testid="profile-loading">
        <div className="relative aspect-square bg-muted animate-pulse" />
        <div className="px-5 pt-5 space-y-4">
          <div className="h-8 bg-muted rounded-2xl animate-pulse w-1/3" />
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="h-20 bg-muted rounded-2xl animate-pulse" />
            ))}
          </div>
          <div className="h-24 bg-muted rounded-2xl animate-pulse" />
          <div className="h-32 bg-muted rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  const peekActive = !!peekUrl && peekLeft > 0;
  const blurred = !c.photo_unlocked && !peekActive;
  const photoUrl = peekActive
    ? photoSrc(peekUrl)
    : (photoSrc(c.photo_url) || "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=900");
  const matchLabel = c.match_score >= 80 ? t("match_label_80") : c.match_score >= 60 ? t("match_label_60") : c.match_score >= 40 ? t("match_label_40") : t("match_label_0");

  return (
    <div data-testid="profile-detail" className="pb-8">
      <div className="relative aspect-square bg-muted">
        <img loading="lazy" decoding="async" src={photoUrl} alt={c.name} className={`w-full h-full object-cover ${blurred ? "blur-photo" : ""}`} />
        <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0" />
        {/* Screenshot deterrent: a faint watermark with the VIEWER's identity
            tiled over the photo. OS screenshots can't be blocked in a web
            app, but any leaked screenshot now identifies who took it. */}
        {!blurred && (
          <div aria-hidden="true" className="absolute inset-0 pointer-events-none select-none overflow-hidden" data-testid="photo-watermark">
            {[18, 48, 78].map((top) => (
              <p
                key={top}
                className="absolute left-0 right-0 text-center text-white whitespace-nowrap"
                style={{ top: `${top}%`, opacity: 0.07, fontSize: 13, letterSpacing: 2, transform: "rotate(-18deg)" }}
              >
                FIDEM · {user?.name || ""} · {(user?.id || "").slice(0, 6)} · FIDEM · {user?.name || ""} · {(user?.id || "").slice(0, 6)}
              </p>
            ))}
          </div>
        )}
        <button data-testid="back-btn" onClick={() => nav(-1)} className="absolute top-4 left-4 glass rounded-full p-2.5">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="absolute top-4 right-4 flex flex-col gap-2 items-end">
          <MatchBadge score={c.match_score} />
        </div>
        {blurred && (
          <div className="absolute inset-0 m-auto h-fit w-fit flex flex-col items-center gap-2">
            <button data-testid="unlock-photo" onClick={unlockPhoto} className="glass-dark text-white rounded-2xl px-5 py-3 flex items-center gap-2">
              <Lock className="w-4 h-4" /> {c.photo_unlock_status === "pending" ? t("photo_requested") : t("unlock_photo")}
            </button>
            {canPeek && (
              <button
                data-testid="peek-photo"
                onClick={peekPhoto}
                disabled={peeking}
                className="glass-dark text-white rounded-2xl px-4 py-2 flex items-center gap-2 text-xs disabled:opacity-50 border border-gold/50"
              >
                <Eye className="w-3.5 h-3.5 text-gold" /> {t("peek_cta")} · {t("peek_once_note")}
              </button>
            )}
          </div>
        )}
        {peekActive && (
          <div data-testid="peek-countdown" className="absolute top-4 left-1/2 -translate-x-1/2 glass-dark text-white rounded-full px-3.5 py-1.5 text-xs font-semibold flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5 text-gold" /> {peekLeft}s
          </div>
        )}
        {/* Incognito reminder: this visit leaves no trace (premium/vip + hidden mode) */}
        {!!user?.hidden_profile && ["premium", "vip"].includes(user?.plan) && (
          <div data-testid="incognito-pill" className="absolute bottom-20 left-4 glass-dark text-white/90 rounded-full px-3 py-1.5 text-[10px] flex items-center gap-1.5">
            <EyeOff className="w-3 h-3" /> {t("privacy_incognito_active")}
          </div>
        )}
        <div className="absolute bottom-4 left-4 right-4 text-white flex items-end justify-between">
          <div>
            <h1 className="font-heading text-3xl font-semibold flex items-center gap-2">
              {c.name}, {c.age} <OnlineDot online={c.online} />
            </h1>
            <p className="text-sm text-white/85">{c.region} · {c.district}{c.distance_bucket ? ` · ${c.distance_bucket} ${t("away")}` : ""} · {formatLastActive(c.last_active_minutes, t, c.online)}</p>
          </div>
        </div>
      </div>

      <div className="px-5 pt-5 space-y-4">
        {/* 15s VIP video intro — plays inline, never autoplays with sound */}
        {c.video_intro_url && (
          <div data-testid="profile-video-intro">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold mb-1.5 flex items-center gap-1.5">
              🎬 {t("video_intro_title")}
            </p>
            <video
              src={photoSrc(c.video_intro_url)}
              controls
              playsInline
              preload="metadata"
              className="w-full rounded-3xl bg-black max-h-72"
            />
          </div>
        )}

        {/* Verification badges row */}
        {(c.verified_selfie || c.verified_financial || c.verified_identity || c.location_verified) && (
          <div className="flex gap-2 flex-wrap" data-testid="profile-badges">
            <VerifiedBadge verified={c.verified_selfie} />
            <FinancialBadge verified={c.verified_financial} />
            <LocationBadge verified={c.location_verified} />
            {c.verified_identity && (
              <span className="inline-flex items-center gap-1 rounded-full bg-secondary/10 text-secondary border border-secondary/25 px-2 py-1 text-[11px] font-medium">
                <Shield className="w-3 h-3" /> {t("identity_badge")}
              </span>
            )}
          </div>
        )}

        {showTierUpsell && (
          <button
            type="button"
            data-testid="profile-tier-upsell"
            onClick={() => {
              posthog.capture("profile_tier_upsell_click", { candidate_id: c.id, candidate_plan: c.plan });
              purchasePlan(c.plan === "vip" ? "vip" : "premium", { t, navigate: nav, onPaid: refresh });
            }}
            className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-gold/15 to-card border border-gold/30 p-3.5 active:scale-[0.98] transition"
          >
            <Crown className="w-5 h-5 text-gold-dark shrink-0" />
            <p className="text-sm flex-1 min-w-0">{t("profile_tier_upsell_hint").replace("{plan}", c.plan === "vip" ? "VIP" : "Premium")}</p>
            <span className="text-xs font-semibold text-gold-dark shrink-0">{t("plan_choose_cta")}</span>
          </button>
        )}

        {/* ---- Section: basic info ---- */}
        <p className="field-label pt-1">{t("pd_section_basic")}</p>

        {/* Key stats — 2 columns on mobile, 3 on larger */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="profile-stats">
          <Stat label={t("height")} value={c.height_cm ? `${c.height_cm} sm` : "—"} />
          <Stat label={t("weight")} value={c.weight_kg ? `${c.weight_kg} kg` : "—"} />
          <Stat label={t("marital_status")} value={t(c.marital_status)} />
          <Stat label={t("has_children")} value={c.has_children ? `${t("yes")}${c.children_count ? ` · ${c.children_count}` : ""}` : t("no")} />
          <Stat label={t("education")} value={c.education || "—"} />
          <Stat label={t("religion")} value={c.religion || "—"} />
          <Stat label={t("smoking")} value={c.smoking ? t(c.smoking) : "—"} />
          <Stat label={t("alcohol")} value={c.alcohol ? t(c.alcohol) : "—"} />
          <Stat label={t("relocation")} value={c.relocation ? t("yes") : t("no")} />
        </div>

        {/* Profession card — separate row for clarity */}
        <div className="rounded-2xl bg-card border border-border p-4">
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">{t("profession")}</p>
          <p className="text-base mt-1 font-medium">{c.profession || "—"}</p>
        </div>

        {c.avg_response_min != null && (
          <div className="rounded-2xl bg-secondary/5 border border-secondary/20 p-3 flex items-center gap-2 text-sm" data-testid="response-speed">
            <Clock className="w-4 h-4 text-secondary shrink-0" />
            <span>
              {t("response_usually")} <strong>{c.avg_response_min < 60 ? `${c.avg_response_min} ${t("minutes")}` : `${Math.round(c.avg_response_min / 60)} ${t("hours")}`}</strong>
            </span>
          </div>
        )}

        {/* ---- Section: personality & interests ---- */}
        <p className="field-label pt-3">{t("pd_section_personality")}</p>

        {c.bio && (
          <div className="rounded-2xl bg-card border border-border p-4">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">{t("bio")}</p>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{c.bio}</p>
          </div>
        )}

        {/* AI Compatibility */}
        <CompatibilityCard targetId={c.id} />

        {/* Prompts */}
        {c.prompts && c.prompts.length > 0 && (
          <div className="space-y-2" data-testid="profile-prompts">
            {c.prompts.map((p, i) => (
              <div key={i} className="rounded-2xl bg-card border border-border p-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{p.text || p.id?.replace("p_", "")}</p>
                {p.kind === "voice" && p.voice_url ? (
                  <audio controls src={photoSrc(p.voice_url)} className="w-full mt-2" />
                ) : (
                  <p className="text-base mt-1 leading-relaxed">{p.answer || "—"}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* match score with reasons */}
        <div className="rounded-2xl border-2 border-secondary/30 bg-secondary/5 p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-heading text-lg font-semibold">{matchLabel}</h3>
            <MatchBadge score={c.match_score} />
          </div>
          <p className="text-xs text-muted-foreground mt-1">{t("why_match")}:</p>
          <ul className="mt-2 space-y-1 stagger">
            {(c.match_reasons || []).map((r, i) => (
              <li key={i} className="text-sm flex items-center gap-2">
                <span className="text-secondary">✓</span> {r}
              </li>
            ))}
          </ul>
        </div>

        {/* actions */}
        <div className="flex gap-2 pt-3">
          <button data-testid="profile-save" onClick={toggleSave} disabled={saving} className={`flex-1 rounded-2xl py-3 inline-flex items-center justify-center gap-2 font-medium border transition ${saved ? "bg-primary text-white border-primary" : "bg-card border-border hover:bg-muted"}`}>
            <Heart key={saved ? "on" : "off"} className={`w-4 h-4 ${saved ? "animate-heart-pop" : ""}`} fill={saved ? "currentColor" : "none"} /> {saved ? t("liked") : t("like")}
          </button>
          <Link data-testid="profile-write" to={`/chat/${c.id}`} className="flex-1 rounded-2xl py-3 inline-flex items-center justify-center gap-2 font-medium bg-secondary text-white">
            <MessageCircle className="w-4 h-4" /> {t("write")}
          </Link>
          <button data-testid="profile-share" onClick={shareProfile} className="rounded-2xl py-3 px-4 bg-card border border-border hover:bg-muted font-medium">
            <Share2 className="w-4 h-4" />
          </button>
        </div>
        {/* Family Share (VIP only) */}
        <button
          data-testid="profile-family"
          onClick={requestFamily}
          disabled={famSending}
          className="w-full rounded-2xl py-2.5 mt-2 text-sm font-medium border border-secondary/40 bg-secondary/10 text-secondary hover:bg-secondary/20 inline-flex items-center justify-center gap-2"
        >
          📞 {t("family_request_btn")}
        </button>
      </div>
    </div>
  );
}

const Stat = memo(function Stat({ label, value }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-3 min-w-0">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{label}</p>
      <p className="text-sm font-semibold mt-1 leading-tight break-words">{value}</p>
    </div>
  );
});
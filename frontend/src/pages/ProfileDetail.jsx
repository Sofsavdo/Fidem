import React, { useState, useCallback, useEffect, memo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import posthog from "posthog-js";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { purchasePlan } from "@/lib/purchase";
import { VerifiedBadge, FinancialBadge, MatchBadge, OnlineDot, LocationBadge } from "@/components/Badges";
import CompatibilityCard from "@/components/CompatibilityCard";
import { photoSrc } from "@/lib/photo";
import { religionLabel, religionKey, educationLabel } from "@/lib/profileValues";
import { track } from "@/lib/analytics";
import PhotoFill from "@/components/PhotoFill";
import { formatLastActive } from "@/lib/time";
import { Heart, MessageCircle, ArrowLeft, Lock, Clock, Shield, Share2, Crown, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useCandidateDetail, useSaved, useToggleSave, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { MATCH_EVENT } from "@/components/MatchCelebration";

export default function ProfileDetail() {
  const { id } = useParams();
  const { t, lang, user, refresh } = useApp();
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

  // Family contact: the asker needs Premium and their own parents' phone on
  // file. A missing phone opens a small form right here instead of a dead
  // "error" toast, then the request goes out.
  const [famSheet, setFamSheet] = useState(false);
  const [famPhone, setFamPhone] = useState("");
  const [famName, setFamName] = useState("");
  const sendFamilyRequest = useCallback(async () => {
    setFamSending(true);
    try {
      await api.post("/family/request", { target_user_id: id, note: "" });
      toast.success(t("family_request_sent"));
      track("family_request_sent");
      return true;
    } catch (e) {
      const d = (e?.response?.data?.detail || "").toString();
      if (d === "family_contact_missing") setFamSheet(true);
      else if (d === "family_already_requested") toast.info(t("family_already_requested"));
      else if (d === "premium_required") { toast.error(t("family_vip_only")); nav("/premium"); }
      else toast.error(t("error_generic"));
      return false;
    } finally { setFamSending(false); }
  }, [id, t, nav]);

  const requestFamily = useCallback(() => {
    if (!user?.is_admin && !["premium", "vip"].includes(user?.plan)) {
      toast.error(t("family_vip_only"));
      nav("/premium");
      return;
    }
    sendFamilyRequest();
  }, [user?.plan, user?.is_admin, t, nav, sendFamilyRequest]);

  const saveFamilyAndSend = useCallback(async () => {
    if (famPhone.replace(/\D/g, "").length < 9) { toast.error(t("family_phone_invalid")); return; }
    setFamSending(true);
    try {
      await api.patch("/family/contacts", { parent_phone: famPhone, parent_name: famName });
    } catch {
      setFamSending(false);
      toast.error(t("family_phone_invalid"));
      return;
    }
    setFamSheet(false);
    await sendFamilyRequest();
  }, [famPhone, famName, t, sendFamilyRequest]);

  const shareProfile = useCallback(async () => {
    const shareText = `${c.name}, ${c.age} — ${c.region}. FIDEM orqali tanishing!`;
    // The bot's username, not the viewer's: the link used to be built from the
    // viewer's own Telegram username, so it opened their chat, not the app.
    const shareUrl = c.share_url || `https://t.me/Fidem_Appbot?start=share_${id}`;
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink && tg.initData) {
      tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`);
      return;
    }
    if (navigator.share) {
      try {
        await navigator.share({ title: `${c.name} — FIDEM`, text: shareText, url: shareUrl });
        return;
      } catch (e) {
        if (e?.name === "AbortError") return; // the person closed the share sheet
      }
    }
    try {
      await navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
      toast.success(t("share_copied"));
    } catch {
      window.prompt(t("share_copied"), shareUrl);
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
  const [slideIdx, setSlideIdx] = useState(0);
  useEffect(() => { setSlideIdx(0); }, [id]);
  useEffect(() => { if (id) track("profile_viewed"); }, [id]);
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
        <div className="relative aspect-[4/5] max-h-[70vh] bg-muted animate-pulse" />
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
    : photoSrc(c.photo_url);
  // Main photo + gallery, swiped through with taps on the left/right of the photo.
  const slides = peekActive ? [photoUrl] : [photoUrl, ...(c.photos || []).map(photoSrc)].filter(Boolean);
  const slide = Math.min(slideIdx, Math.max(0, slides.length - 1));
  const goSlide = (d) => setSlideIdx((i) => Math.max(0, Math.min(slides.length - 1, Math.min(i, slides.length - 1) + d)));
  const matchLabel = c.match_score >= 80 ? t("match_label_80") : c.match_score >= 60 ? t("match_label_60") : c.match_score >= 40 ? t("match_label_40") : t("match_label_0");

  return (
    <div data-testid="profile-detail" className="pb-8">
      <div className="relative aspect-[4/5] max-h-[70vh] w-full overflow-hidden bg-muted">
        <PhotoFill key={slides[slide] || "none"} src={slides[slide] || null} contain className={blurred ? "blur-photo" : ""} />
        <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0" />
        {slides.length > 1 && (
          <>
            <button type="button" aria-label="prev" data-testid="photo-prev" onClick={() => goSlide(-1)} className="absolute inset-y-0 left-0 w-2/5" />
            <button type="button" aria-label="next" data-testid="photo-next" onClick={() => goSlide(1)} className="absolute inset-y-0 right-0 w-2/5" />
            <div className="absolute top-2 inset-x-0 flex justify-center gap-1 pointer-events-none" data-testid="photo-dots">
              {slides.map((_, i) => (
                <span key={i} className={`h-1 rounded-full transition-all ${i === slide ? "w-6 bg-white" : "w-3 bg-white/50"}`} />
              ))}
            </div>
          </>
        )}
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
            <p className="text-sm text-white/85">📍 {c.region} · {c.district}{c.distance_bucket ? ` · ${c.distance_bucket} ${t("away")}` : ""} · {formatLastActive(c.last_active_minutes, t, c.online)}</p>
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
              purchasePlan("premium", { t, navigate: nav, onPaid: refresh });
            }}
            className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-gold/15 to-card border border-gold/30 p-3.5 active:scale-[0.98] transition"
          >
            <Crown className="w-5 h-5 text-gold-dark shrink-0" />
            <p className="text-sm flex-1 min-w-0">{t("profile_tier_upsell_hint").replace("{plan}", "Premium")}</p>
            <span className="text-xs font-semibold text-gold-dark shrink-0">{t("plan_choose_cta")}</span>
          </button>
        )}

        {/* ---- Section: basic info ---- */}
        <p className="field-label pt-1">📋 {t("pd_section_basic")}</p>

        {/* Key facts — each with an emoji that matches the answer, so the
            profile reads at a glance instead of as a list of plain labels. */}
        <div className="grid grid-cols-2 gap-2" data-testid="profile-stats">
          {profileFacts(c, t, lang).map((f, i, all) => (
            <Stat key={f.key} {...f} wide={all.length % 2 === 1 && i === all.length - 1} />
          ))}
        </div>

        {/* Profession card — separate row for clarity */}
        {c.profession && (
          <div className="rounded-2xl bg-card border border-border p-3.5 flex items-center gap-3" data-testid="profile-profession">
            <span className="w-10 h-10 shrink-0 rounded-xl grid place-items-center text-xl bg-indigo-50 dark:bg-indigo-950/40" aria-hidden>💼</span>
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{t("profession")}</p>
              <p className="text-base font-semibold leading-tight break-words">{c.profession}</p>
            </div>
          </div>
        )}

        {c.avg_response_min != null && (
          <div className="rounded-2xl bg-secondary/5 border border-secondary/20 p-3 flex items-center gap-2 text-sm" data-testid="response-speed">
            <Clock className="w-4 h-4 text-secondary shrink-0" />
            <span>
              {t("response_usually")} <strong>{c.avg_response_min < 60 ? `${c.avg_response_min} ${t("minutes")}` : `${Math.round(c.avg_response_min / 60)} ${t("hours")}`}</strong>
            </span>
          </div>
        )}

        {/* ---- Section: personality & interests ---- */}
        <p className="field-label pt-3">✨ {t("pd_section_personality")}</p>

        {c.bio && (
          <div className="rounded-2xl bg-card border border-border p-4">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">✍️ {t("bio")}</p>
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
        {!c.is_ai && <button
          data-testid="profile-family"
          onClick={requestFamily}
          disabled={famSending}
          className="w-full rounded-2xl py-2.5 mt-2 text-sm font-medium border border-secondary/40 bg-secondary/10 text-secondary hover:bg-secondary/20 inline-flex items-center justify-center gap-2"
        >
          📞 {t("family_request_btn")}
        </button>}
        {famSheet && (
          <div className="fixed inset-0 flex items-end" style={{ zIndex: 10001 }} data-testid="family-sheet">
            <div className="absolute inset-0 bg-black/40" onClick={() => setFamSheet(false)} />
            <div className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-5 space-y-3"
              style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))" }}>
              <h3 className="font-heading text-lg font-semibold">{t("family_sheet_title")}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{t("family_sheet_desc")}</p>
              <input data-testid="family-phone" inputMode="tel" placeholder="+998 90 123 45 67" value={famPhone}
                onChange={(e) => setFamPhone(e.target.value)}
                className="w-full px-3.5 py-3 rounded-2xl border border-border bg-background text-sm outline-none focus:border-primary" />
              <input data-testid="family-name" placeholder={t("family_parent_name_ph")} value={famName}
                onChange={(e) => setFamName(e.target.value)}
                className="w-full px-3.5 py-3 rounded-2xl border border-border bg-background text-sm outline-none focus:border-primary" />
              <button data-testid="family-save-send" onClick={saveFamilyAndSend} disabled={famSending} className="btn-primary">
                {famSending ? "..." : t("family_save_send")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const TONES = {
  sky: "bg-sky-50 dark:bg-sky-950/40",
  rose: "bg-rose-50 dark:bg-rose-950/40",
  amber: "bg-amber-50 dark:bg-amber-950/40",
  violet: "bg-violet-50 dark:bg-violet-950/40",
  emerald: "bg-emerald-50 dark:bg-emerald-950/40",
  teal: "bg-teal-50 dark:bg-teal-950/40",
};

const RELIGION_EMOJI = {
  rel_islam: "🕌", rel_christianity: "⛪", rel_judaism: "🕍",
  rel_buddhism: "☸️", rel_hinduism: "🕉️", rel_other: "🙏",
};

const habitEmoji = (v, no, yes) => (v === "no" ? no : v ? yes : "");

// Profile facts with an emoji that fits the answer. Facts the person
// didn't fill in are left out instead of showing a row of dashes.
function profileFacts(c, t, lang) {
  const facts = [
    c.height_cm && { key: "height", emoji: "📏", tone: "sky", label: t("height"), value: `${c.height_cm} sm` },
    c.weight_kg && { key: "weight", emoji: "⚖️", tone: "sky", label: t("weight"), value: `${c.weight_kg} kg` },
    c.marital_status && { key: "marital", emoji: c.marital_status === "single" ? "💫" : "💍", tone: "rose", label: t("marital_status"), value: t(c.marital_status) },
    c.has_children != null && {
      key: "children", emoji: c.has_children ? "👨‍👩‍👧" : "🧸", tone: "rose", label: t("has_children"),
      value: c.has_children ? `${t("yes")}${c.children_count ? ` · ${c.children_count}` : ""}` : t("no"),
    },
    c.education && { key: "education", emoji: "🎓", tone: "violet", label: t("education"), value: educationLabel(c.education, lang) },
    c.religion && { key: "religion", emoji: RELIGION_EMOJI[religionKey(c.religion)] || "🙏", tone: "emerald", label: t("religion"), value: religionLabel(c.religion, t) },
    c.smoking && { key: "smoking", emoji: habitEmoji(c.smoking, "🚭", "🚬"), tone: "amber", label: t("smoking"), value: t(c.smoking) },
    c.alcohol && { key: "alcohol", emoji: habitEmoji(c.alcohol, "🥤", "🍷"), tone: "amber", label: t("alcohol"), value: t(c.alcohol) },
    c.relocation != null && { key: "relocation", emoji: c.relocation ? "✈️" : "🏡", tone: "teal", label: t("relocation"), value: c.relocation ? t("yes") : t("no") },
  ];
  return facts.filter(Boolean);
}

const Stat = memo(function Stat({ emoji, tone, label, value, wide }) {
  return (
    <div className={`rounded-2xl bg-card border border-border p-2.5 min-w-0 flex items-center gap-2.5 ${wide ? "col-span-2" : ""}`} data-testid="profile-fact">
      <span className={`w-9 h-9 shrink-0 rounded-xl grid place-items-center text-lg ${TONES[tone] || "bg-muted"}`} aria-hidden>{emoji}</span>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium leading-tight">{label}</p>
        <p className="text-sm font-semibold mt-0.5 leading-tight break-words">{value}</p>
      </div>
    </div>
  );
});

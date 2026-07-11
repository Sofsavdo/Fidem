import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, Phone, AtSign, Instagram, Save, SlidersHorizontal, ShieldCheck, Lock, Video, Trash2, Crown } from "lucide-react";
import { useDailyStatus, QK } from "@/hooks/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { photoSrc } from "@/lib/photo";

// Client-side duration probe: reject anything over ~16s before uploading.
function probeVideoDuration(file) {
  return new Promise((resolve) => {
    try {
      const url = URL.createObjectURL(file);
      const v = document.createElement("video");
      v.preload = "metadata";
      v.onloadedmetadata = () => { URL.revokeObjectURL(url); resolve(v.duration || 0); };
      v.onerror = () => { URL.revokeObjectURL(url); resolve(0); };
      v.src = url;
    } catch {
      resolve(0);
    }
  });
}

// "Sozlamalar" — the Me page's settings sub-screen: shareable contact info
// (phone / telegram / instagram, used by the chat's share-contact button),
// the daily streak, and links to the remaining preference screens.
export default function MeSettings() {
  const { t, user, refresh } = useApp();
  const queryClient = useQueryClient();
  const { data: daily } = useDailyStatus();

  const [phone, setPhone] = useState(user?.contact_phone || "");
  const [tg, setTg] = useState(user?.contact_telegram || "");
  const [ig, setIg] = useState(user?.contact_instagram || "");

  const saveMutation = useMutation({
    mutationFn: () => api.patch("/profile", {
      contact_phone: phone.trim(),
      contact_telegram: tg.trim().replace(/^@/, ""),
      contact_instagram: ig.trim().replace(/^@/, ""),
    }),
    onSuccess: async () => { toast.success(t("save") + " ✓"); await refresh(); },
    onError: () => toast.error(t("error_generic")),
  });

  const claimDailyMutation = useMutation({
    mutationFn: () => api.post("/daily/claim"),
    onSuccess: (r) => {
      toast.success(`+${r.data.bonus} ${t("sum")}`);
      queryClient.invalidateQueries({ queryKey: QK.dailyStatus });
      refresh();
    },
    onError: () => toast.error(t("error_generic")),
  });

  const isPaidPlan = ["standard", "premium", "vip"].includes(user?.plan);
  const isVip = user?.plan === "vip";

  // 15s VIP video intro
  const fileRef = useRef(null);
  const [videoBusy, setVideoBusy] = useState(false);
  const onVideoPicked = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error(t("video_too_big")); return; }
    const dur = await probeVideoDuration(file);
    if (dur > 16) { toast.error(t("video_too_long")); return; }
    setVideoBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const up = await api.post("/files/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      await api.patch("/profile", { video_intro_url: up.data.url });
      await refresh();
      toast.success(t("video_saved"));
    } catch (err) {
      const detail = (err?.response?.data?.detail || "").toString();
      toast.error(detail === "video_requires_vip" ? t("video_requires_vip") : t("error_generic"));
    } finally {
      setVideoBusy(false);
    }
  };
  const removeVideo = async () => {
    setVideoBusy(true);
    try {
      await api.patch("/profile", { video_intro_url: "" });
      await refresh();
      toast.success(t("video_removed"));
    } catch {
      toast.error(t("error_generic"));
    } finally {
      setVideoBusy(false);
    }
  };

  if (!user) return null;

  return (
    <div>
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="mesettings-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-semibold text-lg">{t("me_settings_title")}</span>
      </header>

      <div className="max-w-2xl mx-auto p-4 md:p-6 space-y-5">
        {/* Contact info — what the chat's "share contact" button sends */}
        <div className="rounded-3xl bg-card border border-border p-5 space-y-3" data-testid="contact-info-card">
          <div>
            <h2 className="font-semibold">{t("contact_info_title")}</h2>
            <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{t("contact_info_hint")}</p>
          </div>
          {!isPaidPlan && (
            <div className="flex items-start gap-2 rounded-2xl bg-muted/60 border border-border px-3 py-2">
              <Lock className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {t("contact_paid_note")}{" "}
                <Link to="/premium?tab=plans" className="text-primary underline">{t("privacy_choose_plan")}</Link>
              </p>
            </div>
          )}
          <label className="block">
            <span className="field-label flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" /> {t("contact_phone_label")}</span>
            <input
              data-testid="contact-phone"
              inputMode="tel"
              placeholder="+998 90 123 45 67"
              className="mt-1.5 w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="field-label flex items-center gap-1.5"><AtSign className="w-3.5 h-3.5" /> Telegram</span>
            <input
              data-testid="contact-telegram"
              placeholder="username"
              className="mt-1.5 w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm"
              value={tg}
              onChange={(e) => setTg(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="field-label flex items-center gap-1.5"><Instagram className="w-3.5 h-3.5" /> Instagram</span>
            <input
              data-testid="contact-instagram"
              placeholder="username"
              className="mt-1.5 w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm"
              value={ig}
              onChange={(e) => setIg(e.target.value)}
            />
          </label>
          <button
            data-testid="contact-save"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="w-full rounded-2xl bg-primary text-white text-sm font-medium py-2.5 disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
          >
            <Save className="w-4 h-4" /> {t("save")}
          </button>
        </div>

        {/* 15s video intro — VIP perk that proves seriousness on the profile */}
        <div className="rounded-3xl bg-card border border-border p-5 space-y-3" data-testid="video-intro-card">
          <div>
            <h2 className="font-semibold flex items-center gap-1.5"><Video className="w-4 h-4" /> {t("video_intro_title")} <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gold/15 text-gold-dark font-bold uppercase">VIP</span></h2>
            <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{t("video_intro_hint")}</p>
          </div>
          {user.video_intro_url ? (
            <>
              <video
                src={photoSrc(user.video_intro_url)}
                controls
                playsInline
                preload="metadata"
                className="w-full rounded-2xl bg-black max-h-64"
                data-testid="video-intro-player"
              />
              <button
                data-testid="video-intro-remove"
                onClick={removeVideo}
                disabled={videoBusy}
                className="w-full rounded-2xl bg-muted text-sm font-medium py-2.5 disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
              >
                <Trash2 className="w-4 h-4" /> {t("video_remove_btn")}
              </button>
            </>
          ) : isVip ? (
            <>
              <input ref={fileRef} type="file" accept="video/mp4,video/quicktime" className="hidden" onChange={onVideoPicked} data-testid="video-intro-input" />
              <button
                data-testid="video-intro-upload"
                onClick={() => fileRef.current?.click()}
                disabled={videoBusy}
                className="w-full rounded-2xl bg-primary text-white text-sm font-medium py-2.5 disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
              >
                <Video className="w-4 h-4" /> {videoBusy ? "..." : t("video_upload_btn")}
              </button>
            </>
          ) : (
            <Link
              to="/premium?tab=plans&hl=vip"
              data-testid="video-intro-vip-cta"
              className="flex items-center justify-center gap-1.5 rounded-2xl bg-primary/10 border border-primary/25 px-4 py-2.5 text-sm font-semibold text-primary active:scale-[0.98] transition"
            >
              <Crown className="w-4 h-4" /> {t("privacy_get_vip")}
            </Link>
          )}
        </div>

        {/* Daily streak — moved here from the Me front page */}
        {daily && (
          <div className="rounded-3xl bg-gradient-to-r from-gold/15 to-card border border-gold/30 p-4" data-testid="daily-strip">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("daily_streak")}</p>
                <p className="font-heading text-2xl">{daily.streak} {t("day_word")} 🔥</p>
              </div>
              {daily.claimed_today ? (
                <span className="text-xs text-secondary font-medium">✓ {t("daily")}</span>
              ) : (
                <button
                  data-testid="daily-claim-inline"
                  onClick={() => claimDailyMutation.mutate()}
                  disabled={claimDailyMutation.isPending}
                  className="rounded-xl bg-gold text-ink px-4 py-2 text-sm font-medium disabled:opacity-60"
                >
                  +{daily.next_bonus} {t("sum")}
                </button>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-2 leading-snug">{t("streak_explain")}</p>
          </div>
        )}

        {/* Remaining preference screens */}
        <div className="rounded-3xl bg-card border border-border divide-y">
          <Link to="/settings" data-testid="link-message-filters" className="flex items-center justify-between p-4">
            <span className="flex items-center gap-3 text-sm"><SlidersHorizontal className="w-4 h-4" /> {t("who_can_message_me")}</span>
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </Link>
          <Link to="/terms" data-testid="link-legal" className="flex items-center justify-between p-4">
            <span className="flex items-center gap-3 text-sm"><ShieldCheck className="w-4 h-4 text-muted-foreground" /> {t("legal_links_title")}</span>
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </Link>
        </div>
      </div>
    </div>
  );
}

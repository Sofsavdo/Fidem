import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { VerifiedBadge, FinancialBadge, MatchBadge, OnlineDot } from "@/components/Badges";
import GiftModal from "@/components/GiftModal";
import RoseModal from "@/components/RoseModal";
import CompatibilityCard from "@/components/CompatibilityCard";
import { photoSrc } from "@/lib/photo";
import { Bookmark, MessageCircle, Gift, ArrowLeft, Lock, Clock, Shield } from "lucide-react";
import { toast } from "sonner";

export default function ProfileDetail() {
  const { id } = useParams();
  const { t } = useApp();
  const nav = useNavigate();
  const [c, setC] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [giftOpen, setGiftOpen] = useState(false);
  const [roseOpen, setRoseOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/candidates/${id}`);
      setC(r.data);
      const my = await api.get("/saved/mine");
      setSaved((my.data || []).some((x) => x.id === id));
    } catch (e) {
      toast.error("Xato");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const unlockPhoto = async () => {
    try {
      const r = await api.post("/photo-unlock/request", { target_user_id: id });
      toast.success(r.data.status === "approved" ? "Rasm ochildi" : "So'rov yuborildi");
      load();
    } catch (e) { toast.error("Xato"); }
  };
  const toggleSave = async () => {
    setSaving(true);
    try {
      if (saved) { await api.delete(`/saved/${id}`); setSaved(false); }
      else { await api.post("/saved", { user_id: id }); setSaved(true); toast.success("Saqlandi"); }
    } finally { setSaving(false); }
  };
  const sendGift = () => setGiftOpen(true);

  if (loading || !c) {
    return <div className="p-6 text-center text-muted-foreground" data-testid="profile-loading">{t("loading")}</div>;
  }

  const blurred = !c.photo_unlocked;
  const photoUrl = photoSrc(c.photo_url) || "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=900";
  const matchLabel = c.match_score >= 80 ? t("match_label_80") : c.match_score >= 60 ? t("match_label_60") : c.match_score >= 40 ? t("match_label_40") : t("match_label_0");

  return (
    <div data-testid="profile-detail" className="pb-8">
      <div className="relative aspect-square bg-muted">
        <img src={photoUrl} alt={c.name} className={`w-full h-full object-cover ${blurred ? "blur-photo" : ""}`} />
        <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0" />
        <button data-testid="back-btn" onClick={() => nav(-1)} className="absolute top-4 left-4 glass rounded-full p-2.5">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="absolute top-4 right-4 flex flex-col gap-2 items-end">
          <MatchBadge score={c.match_score} />
        </div>
        {blurred && (
          <button data-testid="unlock-photo" onClick={unlockPhoto} className="absolute inset-0 m-auto h-fit w-fit glass-dark text-white rounded-2xl px-5 py-3 flex items-center gap-2">
            <Lock className="w-4 h-4" /> {c.photo_unlock_status === "pending" ? t("photo_requested") : t("unlock_photo")}
          </button>
        )}
        <div className="absolute bottom-4 left-4 right-4 text-white flex items-end justify-between">
          <div>
            <h1 className="font-heading text-3xl font-semibold flex items-center gap-2">
              {c.name}, {c.age} <OnlineDot online={c.online} />
            </h1>
            <p className="text-sm text-white/85">{c.region} · {c.district} · {c.last_active_label}</p>
          </div>
        </div>
      </div>

      <div className="px-5 pt-5 space-y-5">
        <div className="flex gap-2 flex-wrap">
          <VerifiedBadge verified={c.verified_selfie} />
          <FinancialBadge verified={c.verified_financial} />
          {c.verified_identity && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 text-[10px]">
              <Shield className="w-3 h-3" /> Identity
            </span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 text-sm">
          <Stat label={t("height")} value={`${c.height_cm} sm`} />
          <Stat label={t("weight")} value={`${c.weight_kg} kg`} />
          <Stat label={t("marital_status")} value={t(c.marital_status)} />
          <Stat label={t("has_children")} value={c.has_children ? `${t("yes")} ${c.children_count ? "(" + c.children_count + ")" : ""}` : t("no")} />
          <Stat label={t("education")} value={c.education || "—"} />
          <Stat label={t("religion")} value={c.religion || "—"} />
        </div>

        {c.avg_response_min != null && (
          <div className="rounded-2xl bg-card border border-border p-3 flex items-center gap-2 text-sm" data-testid="response-speed">
            <Clock className="w-4 h-4 text-secondary" />
            <span>
              {t("response_usually")} <strong>{c.avg_response_min < 60 ? `${c.avg_response_min} ${t("minutes")}` : `${Math.round(c.avg_response_min / 60)} ${t("hours")}`}</strong>
            </span>
          </div>
        )}

        {c.bio && (
          <div className="rounded-2xl bg-card border border-border p-4">
            <p className="text-sm leading-relaxed">{c.bio}</p>
          </div>
        )}
        <div className="rounded-2xl bg-card border border-border p-4">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("profession")}</p>
          <p className="text-base mt-1">{c.profession || "—"}</p>
        </div>

        {/* AI Compatibility */}
        <CompatibilityCard targetId={c.id} lang="uz" />

        {/* Prompts */}
        {c.prompts && c.prompts.length > 0 && (
          <div className="space-y-2" data-testid="profile-prompts">
            {c.prompts.map((p, i) => (
              <div key={i} className="rounded-2xl bg-card border border-border p-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{p.text || p.id?.replace("p_", "")}</p>
                {p.kind === "voice" && p.voice_url ? (
                  <audio controls src={p.voice_url} className="w-full mt-2" />
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
        <div className="flex gap-2 sticky bottom-24 pt-3">
          <button data-testid="profile-save" onClick={toggleSave} disabled={saving} className={`flex-1 rounded-2xl py-3 inline-flex items-center justify-center gap-2 font-medium border transition ${saved ? "bg-primary text-white border-primary" : "bg-card border-border hover:bg-muted"}`}>
            <Bookmark className="w-4 h-4" fill={saved ? "currentColor" : "none"} /> {t("save")}
          </button>
          <Link data-testid="profile-write" to={`/chat/${c.id}`} className="flex-1 rounded-2xl py-3 inline-flex items-center justify-center gap-2 font-medium bg-secondary text-white">
            <MessageCircle className="w-4 h-4" /> {t("write")}
          </Link>
          <button data-testid="profile-rose" onClick={() => setRoseOpen(true)} className="rounded-2xl py-3 px-4 bg-primary/10 text-primary font-medium text-xl">
            🌹
          </button>
          <button data-testid="profile-gift" onClick={sendGift} className="rounded-2xl py-3 px-4 bg-gold text-ink font-medium">
            <Gift className="w-4 h-4" />
          </button>
        </div>
      </div>
      {giftOpen && <GiftModal targetId={c.id} targetName={c.name} onClose={() => setGiftOpen(false)} />}
      {roseOpen && <RoseModal targetId={c.id} targetName={c.name} onClose={() => setRoseOpen(false)} onSent={load} />}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-3">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="text-sm font-medium mt-0.5 truncate">{value}</p>
    </div>
  );
}
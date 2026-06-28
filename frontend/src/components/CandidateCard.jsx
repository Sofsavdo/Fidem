import React from "react";
import { Link } from "react-router-dom";
import { Bookmark, MessageCircle, Lock } from "lucide-react";
import { VerifiedBadge, FinancialBadge, MatchBadge, OnlineDot } from "@/components/Badges";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { formatLastActive } from "@/lib/time";

export default function CandidateCard({ c, onSave, saved }) {
  const { t } = useApp();
  const blurred = !c.photo_unlocked;
  const photoUrl = photoSrc(c.photo_url) || "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=800";

  return (
    <div
      data-testid={`candidate-card-${c.id}`}
      className="bg-card rounded-3xl overflow-hidden shadow-soft hover:shadow-elevated transition-shadow border border-border/60"
    >
      <Link to={`/candidate/${c.id}`} className="block">
        <div className="relative aspect-[4/5] overflow-hidden bg-muted">
          <img
            src={photoUrl}
            alt={c.name}
            loading="lazy"
            decoding="async"
            className={`w-full h-full object-cover transition-all duration-700 ${blurred ? "blur-photo" : ""}`}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/0 to-black/0" />

          {/* Top row: match score + badges */}
          <div className="absolute top-3 left-3 right-3 flex items-start justify-between">
            <div className="flex flex-col gap-1">
              <MatchBadge score={c.match_score ?? 0} />
              {c.spotlight && (
                <span data-testid="badge-spotlight" className="inline-flex items-center gap-1 text-[9px] bg-gold text-ink rounded-full px-2 py-0.5 font-semibold">
                  ★ Spotlight
                </span>
              )}
              {c.boosted && !c.spotlight && (
                <span data-testid="badge-boost" className="inline-flex items-center gap-1 text-[9px] bg-primary text-white rounded-full px-2 py-0.5 font-semibold">
                  🚀 Boost
                </span>
              )}
            </div>
            <div className="flex flex-col gap-1 items-end">
              <VerifiedBadge verified={c.verified_selfie} />
              <FinancialBadge verified={c.verified_financial} />
            </div>
          </div>

          {/* Blur overlay hint */}
          {blurred && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="glass-dark text-white rounded-full px-3 py-1.5 text-xs flex items-center gap-1.5">
                <Lock className="w-3 h-3" /> {t("photo_locked")}
              </div>
            </div>
          )}

          {/* Bottom name/region */}
          <div className="absolute bottom-3 left-3 right-3 text-white">
            <div className="flex items-center gap-2">
              <h3 className="font-heading text-xl font-semibold leading-tight">
                {c.name}, {c.age}
              </h3>
              <OnlineDot online={c.online} />
            </div>
            <p className="text-xs text-white/85 mt-0.5">
              {c.region} · {formatLastActive(c.last_active_minutes, t, c.online)}
            </p>
          </div>
        </div>
      </Link>

      <div className="p-3 flex items-center justify-between gap-2">
        <Link
          to={`/candidate/${c.id}`}
          data-testid={`candidate-open-${c.id}`}
          className="text-xs font-medium text-primary hover:underline"
        >
          {t("open_profile")} →
        </Link>
        <div className="flex items-center gap-1.5">
          <button
            data-testid={`candidate-save-${c.id}`}
            onClick={() => onSave?.(c)}
            className={`p-2 rounded-full transition ${
              saved ? "bg-primary text-white" : "bg-muted text-foreground hover:bg-border"
            }`}
            title={t("save")}
          >
            <Bookmark className="w-4 h-4" fill={saved ? "currentColor" : "none"} />
          </button>
          <Link
            to={`/chat/${c.id}`}
            data-testid={`candidate-message-${c.id}`}
            className="p-2 rounded-full bg-secondary text-white hover:bg-secondary/90"
            title={t("write")}
          >
            <MessageCircle className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

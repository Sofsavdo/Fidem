import React, { memo, useCallback } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Bookmark, MessageCircle, Lock, MapPin, BadgeCheck } from "lucide-react";
import { MatchBadge, OnlineDot } from "@/components/Badges";
import { useApp } from "@/contexts/AppContext";
import { QK } from "@/hooks/queries";
import api from "@/lib/api";
import { photoSrc } from "@/lib/photo";
import { formatLastActive } from "@/lib/time";

function CandidateCardInner({ c, onSave, saved }) {
  const { t } = useApp();
  const queryClient = useQueryClient();
  const blurred = !c.photo_unlocked;
  const photoUrl = photoSrc(c.photo_url) || "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=800";

  // Warm the profile-detail query on touch so opening the profile feels instant.
  const prefetchDetail = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: QK.candidateDetail(c.id),
      queryFn: () => api.get(`/candidates/${c.id}`).then((r) => r.data),
      staleTime: 30_000,
    });
  }, [queryClient, c.id]);

  return (
    <div
      data-testid={`candidate-card-${c.id}`}
      className="bg-card rounded-3xl overflow-hidden shadow-soft hover:shadow-elevated transition-shadow border border-border/60"
    >
      <Link to={`/candidate/${c.id}`} className="block" onPointerDown={prefetchDetail} onMouseEnter={prefetchDetail}>
        <div className="relative aspect-[4/5] overflow-hidden bg-muted">
          <img
            src={photoUrl}
            alt={c.name}
            loading="lazy"
            decoding="async"
            className={`w-full h-full object-cover transition-all duration-700 ${blurred ? "blur-photo" : ""}`}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0" />

          {/* One small match pill — the rest of the badges live in the profile. */}
          <div className="absolute top-3 left-3">
            <MatchBadge score={c.match_score ?? 0} />
          </div>

          {blurred && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="glass-dark text-white rounded-full px-3 py-1.5 text-xs flex items-center gap-1.5">
                <Lock className="w-3 h-3" /> {t("photo_locked")}
              </div>
            </div>
          )}

          {/* Bottom: name (+ tiny verified tick), online dot, then the only meta
              that matters at a glance — where, distance, last active. */}
          <div className="absolute bottom-3 left-3 right-3 text-white">
            <div className="flex items-center gap-1.5 min-w-0">
              <h3 className="font-heading text-xl font-semibold leading-tight truncate">
                {c.name}, {c.age}
              </h3>
              {c.verified_selfie && <BadgeCheck className="w-4 h-4 shrink-0 text-sky-300" title={t("verified")} />}
              <OnlineDot online={c.online} />
            </div>
            <p className="text-xs text-white/85 mt-0.5 flex items-center gap-1 truncate">
              <MapPin className="w-3 h-3 shrink-0" />
              {c.region}
              {c.distance_bucket ? ` · ${c.distance_bucket} ${t("away")}` : ""}
              {" · "}{formatLastActive(c.last_active_minutes, t, c.online)}
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

export default memo(CandidateCardInner);

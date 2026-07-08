import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Heart, X } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

// Fired by any save-toggle site (Candidates, ProfileDetail) when the backend
// reports the save just completed a mutual match. Mounted once in Layout so
// it works regardless of which page the save happened on.
export const MATCH_EVENT = "fidem:match";

export default function MatchCelebration() {
  const { t } = useApp();
  const [candidate, setCandidate] = useState(null);

  useEffect(() => {
    const onMatch = (e) => setCandidate(e.detail);
    window.addEventListener(MATCH_EVENT, onMatch);
    return () => window.removeEventListener(MATCH_EVENT, onMatch);
  }, []);

  if (!candidate) return null;

  const close = () => setCandidate(null);

  return (
    <div className="fixed inset-0 z-[10001] flex items-center justify-center p-6" data-testid="match-celebration">
      <div className="absolute inset-0 bg-ink/70 backdrop-blur-sm" onClick={close} />
      <div className="relative w-full max-w-sm rounded-3xl bg-card overflow-hidden shadow-2xl">
        <div className="relative overflow-hidden bg-gradient-to-br from-primary to-secondary p-8 text-center text-white">
          <div className="orb orb-1" />
          <div className="orb orb-2" />
          <button onClick={close} className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-white/15 hover:bg-white/25">
            <X className="w-4 h-4" />
          </button>
          <div className="relative z-10">
            <Heart className="w-10 h-10 mx-auto mb-3" fill="currentColor" />
            <h2 className="font-heading text-2xl font-semibold">{t("match_celebration_title")}</h2>
          </div>
        </div>
        <div className="p-6 text-center space-y-4">
          <p className="text-sm text-muted-foreground">
            {t("match_celebration_desc").replace("{name}", candidate.name || "")}
          </p>
          <Link
            to={`/chat/${candidate.id}`}
            onClick={close}
            data-testid="match-celebration-cta"
            className="block w-full rounded-2xl bg-primary text-white py-3 font-medium"
          >
            {t("match_celebration_cta")}
          </Link>
          <button onClick={close} className="text-xs text-muted-foreground">
            {t("match_celebration_dismiss")}
          </button>
        </div>
      </div>
    </div>
  );
}

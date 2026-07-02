import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Trophy } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

export default function ProgressCard() {
  const { t, lang } = useApp();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get(`/me/progress?lang=${lang}`).then((r) => setData(r.data)).catch(() => {});
  }, [lang]);

  if (!data) return null;
  const earned = data.badges.filter((b) => b.achieved);

  // Simplified: only show badges, hide XP/levels
  return (
    <div className="rounded-3xl bg-card border border-border p-4" data-testid="progress-card">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 rounded-2xl bg-secondary/10 text-secondary grid place-items-center">
          <Trophy className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <p className="font-heading font-semibold">Yutuqlar</p>
          <p className="text-xs text-muted-foreground">
            {data.badges_earned}/{data.badges_total} badge
          </p>
        </div>
      </div>

      {earned.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {earned.map((b) => (
            <span key={b.id} title={b.name} className="inline-flex items-center gap-1 rounded-full bg-secondary/10 text-secondary text-xs px-2 py-1">
              <span>{b.icon}</span> {b.name}
            </span>
          ))}
        </div>
      )}
      {earned.length === 0 && (
        <p className="text-xs text-muted-foreground">Hali yutuqlar yo'q</p>
      )}
    </div>
  );
}

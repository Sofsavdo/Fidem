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
  const locked = data.badges.filter((b) => !b.achieved);

  return (
    <div className="rounded-3xl bg-card border border-border p-4" data-testid="progress-card">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 rounded-2xl bg-secondary/10 text-secondary grid place-items-center">
          <Trophy className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <p className="font-heading font-semibold">{data.title}</p>
          <p className="text-xs text-muted-foreground">
            {t("progress_level_xp").replace("{level}", data.level).replace("{xp}", data.xp)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground">{t("progress_badges")}</p>
          <p className="font-medium text-sm">{data.badges_earned}/{data.badges_total}</p>
        </div>
      </div>
      <div className="w-full h-2 bg-muted rounded-full overflow-hidden mb-1">
        <div className="h-full bg-gradient-to-r from-secondary to-primary transition-all" style={{ width: `${data.progress_pct}%` }} />
      </div>
      <p className="text-[11px] text-muted-foreground text-center">
        {t("progress_next_level").replace("{xp}", data.xp_to_next)}
      </p>

      {earned.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/60">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">{t("progress_earned")}</p>
          <div className="flex flex-wrap gap-1.5">
            {earned.map((b) => (
              <span key={b.id} title={b.name} className="inline-flex items-center gap-1 rounded-full bg-secondary/10 text-secondary text-xs px-2 py-1">
                <span>{b.icon}</span> {b.name}
              </span>
            ))}
          </div>
        </div>
      )}
      {locked.length > 0 && (
        <details className="mt-2">
          <summary className="text-[10px] uppercase tracking-wider text-muted-foreground cursor-pointer">
            {t("progress_locked")} ({locked.length})
          </summary>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {locked.map((b) => (
              <span key={b.id} title={b.name} className="inline-flex items-center gap-1 rounded-full bg-muted text-muted-foreground text-xs px-2 py-1 opacity-60">
                <span>{b.icon}</span> {b.name}
              </span>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

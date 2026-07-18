import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Sparkles, X, Gift } from "lucide-react";
import { toast } from "sonner";

export default function DailyCheckIn() {
  const { user, refresh, t } = useApp();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [claiming, setClaiming] = useState(false);

  useEffect(() => {
    if (!user || !user.onboarded) return;
    const today = new Date().toISOString().slice(0, 10);
    // Skip the one time a user lands here straight out of onboarding - they
    // haven't seen the app yet, and this would bury the "profile ready"
    // toast under a gamification modal before they've even seen a candidate.
    if (sessionStorage.getItem("fidem_just_onboarded")) {
      sessionStorage.removeItem("fidem_just_onboarded");
      localStorage.setItem("fidem_daily_shown", today);
      return;
    }
    const lastShown = localStorage.getItem("fidem_daily_shown");
    if (lastShown === today) return;
    api.get("/daily/status").then((r) => {
      setStatus(r.data);
      // A completed 7-day ladder retires for this user - never re-open.
      if (!r.data.completed && !r.data.claimed_today) setOpen(true);
      localStorage.setItem("fidem_daily_shown", today);
    });
  }, [user]);

  if (!open || !status) return null;

  const claim = async () => {
    setClaiming(true);
    try {
      const r = await api.post("/daily/claim");
      toast.success(`+${r.data.bonus} ${t("sum")} · ${r.data.streak} ${t("day_word")}`);
      await refresh();
      setOpen(false);
    } catch (e) {
      toast.error(t("error_generic"));
    } finally {
      setClaiming(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center px-4" style={{ zIndex: 10001 }} data-testid="daily-checkin">
      <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-sm bg-card rounded-3xl p-6 text-center animate-fade-up shadow-elevated">
        <button onClick={() => setOpen(false)} data-testid="daily-close" className="absolute right-3 top-3 p-1.5 rounded-full hover:bg-muted">
          <X className="w-4 h-4" />
        </button>
        <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-gold to-gold-dark grid place-items-center text-white">
          <Sparkles className="w-7 h-7" />
        </div>
        <h2 className="font-heading text-2xl font-semibold mt-3">{t("daily_bonus") || "Daily bonus"}</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {(status.next_streak || 1)}-{t("day_word")} ·{" "}
          <span className="text-foreground font-semibold">+{(status.next_bonus || 0).toLocaleString()} {t("sum")}</span>
        </p>
        {/* Doubling ladder: today's step highlighted, so the user SEES what
            tomorrow pays and what a missed day costs. */}
        <div className="flex justify-center gap-1 mt-4">
          {(status.rewards || [100, 200, 400, 800, 1600, 3200, 6400]).map((amt, i) => {
            const day = Math.min(status.next_streak || 1, 7);
            const filled = i < day - 1;
            const isToday = i === day - 1;
            return (
              <div key={i} className="flex flex-col items-center gap-0.5">
                <div
                  className={`w-9 h-7 rounded-lg grid place-items-center text-[9px] font-semibold tabular-nums ${
                    filled ? "bg-gold/70 text-ink" : isToday ? "bg-primary text-white ring-2 ring-primary/30" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {amt >= 1000 ? `${(amt / 1000).toFixed(1).replace(".0", "")}k` : amt}
                </div>
                <span className={`text-[8px] ${isToday ? "text-primary font-semibold" : "text-muted-foreground"}`}>{i + 1}</span>
              </div>
            );
          })}
        </div>
        <p className="text-[11px] text-muted-foreground mt-3">{t("streak_tomorrow_hint").replace("{n}", (status.tomorrow_bonus || 0).toLocaleString())}</p>
        <button
          data-testid="daily-claim"
          onClick={claim}
          disabled={claiming}
          className="mt-5 w-full rounded-2xl bg-primary text-white py-3 font-medium disabled:opacity-50"
        >
          <Gift className="w-4 h-4 inline mr-1.5" />
          {claiming ? "..." : (t("claim_weeks") || "Claim")}
        </button>
      </div>
    </div>
  );
}

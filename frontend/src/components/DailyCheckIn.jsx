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
      if (!r.data.claimed_today) setOpen(true);
      localStorage.setItem("fidem_daily_shown", today);
    });
  }, [user]);

  if (!open || !status) return null;

  const claim = async () => {
    setClaiming(true);
    try {
      const r = await api.post("/daily/claim");
      toast.success(`+${r.data.bonus} 🪙 · ${r.data.streak} ${t("day_word")}`);
      await refresh();
      setOpen(false);
    } catch (e) {
      toast.error(t("error_generic"));
    } finally {
      setClaiming(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" data-testid="daily-checkin">
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
          {status.streak} {t("day_word")} ·{" "}
          <span className="text-foreground font-semibold">+{status.next_bonus} 🪙</span>
        </p>
        <div className="flex justify-center gap-1.5 mt-4">
          {Array.from({ length: 7 }).map((_, i) => {
            const filled = i < (status.streak % 7);
            const isToday = i === (status.streak % 7);
            return (
              <div
                key={i}
                className={`w-7 h-7 rounded-full grid place-items-center text-[10px] font-medium ${
                  filled ? "bg-gold text-ink" : isToday ? "bg-primary text-white ring-2 ring-primary/30" : "bg-muted text-muted-foreground"
                }`}
              >
                {i + 1}
              </div>
            );
          })}
        </div>
        <p className="text-[11px] text-muted-foreground mt-3">7 {t("day_word")} · +100 🪙 🎁</p>
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

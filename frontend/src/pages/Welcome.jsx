import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Heart, Check, Sparkles } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import LangSwitch from "@/components/LangSwitch";

export default function Welcome() {
  const { t, user } = useApp();
  const nav = useNavigate();

  const trustItems = [
    { t: "land_trust1_t", s: "land_trust1_s" },
    { t: "land_trust2_t", s: "land_trust2_s" },
    { t: "land_trust3_t", s: "land_trust3_s" },
  ];

  // Mark welcome as seen, then route: an already-authenticated user (Telegram
  // first-timer) goes straight to onboarding; a web visitor goes to auth.
  const start = () => {
    try { localStorage.setItem("fidem_welcomed", "1"); } catch { /* ignore */ }
    nav(user ? "/onboarding" : "/auth");
  };

  return (
    <div className="relative h-[100dvh] bg-ink text-white overflow-hidden flex flex-col">
      {/* Ambient glow orbs — no external images, renders instantly */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="orb orb-1 opacity-40" />
        <div className="orb orb-2 opacity-25" />
        <div className="orb orb-3 opacity-20" />
      </div>

      <header className="relative z-10 flex items-center justify-between px-5 pt-4">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-gold grid place-items-center text-white">
            <Heart className="w-5 h-5" fill="currentColor" />
          </div>
          <span className="font-heading font-bold text-xl tracking-tight">FIDEM</span>
        </div>
        <LangSwitch />
      </header>

      <main className="relative z-10 flex-1 flex flex-col justify-center px-6 py-5 max-w-md mx-auto w-full text-center">
        <div className="inline-flex mx-auto items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-full bg-white/10 border border-white/15 backdrop-blur-sm">
          <Sparkles className="w-3.5 h-3.5 text-gold" /> {t("land_badge")}
        </div>

        <h1 className="mt-4 font-heading text-3xl sm:text-5xl font-bold leading-[1.1] tracking-tight">
          {t("land_hero_a")}<span className="text-gold">{t("land_hero_em")}</span>{t("land_hero_b")}
        </h1>

        <p className="mt-3 text-white/65 text-sm sm:text-[15px] leading-relaxed max-w-sm mx-auto">
          {t("land_subtitle")}
        </p>

        <div className="mt-5 space-y-2 text-left">
          {trustItems.map((item, i) => (
            <div key={i} className="flex items-center gap-3 bg-white/[0.06] border border-white/10 rounded-2xl px-4 py-2.5">
              <div className="w-6 h-6 rounded-full bg-gold/20 grid place-items-center shrink-0">
                <Check className="w-3.5 h-3.5 text-gold" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium leading-tight">{t(item.t)}</p>
                <p className="text-[11px] text-white/50 leading-tight">{t(item.s)}</p>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={start}
          data-testid="land-cta-primary"
          className="mt-5 block w-full rounded-2xl bg-gradient-to-r from-primary to-primary/90 text-white font-semibold text-base py-4 shadow-lg shadow-primary/30 hover:-translate-y-0.5 active:scale-[0.98] transition"
        >
          {t("welcome_cta_primary")}
        </button>

        <p className="mt-3 text-xs text-white/45">{t("land_social_proof")}</p>
      </main>

      <footer className="relative z-10 text-center text-[11px] text-white/35 pb-6 px-6 flex items-center justify-center gap-4">
        <Link to="/about" data-testid="footer-about" className="hover:text-white/70 transition-colors">{t("land_about")}</Link>
        <span className="opacity-30">·</span>
        <Link to="/faq" data-testid="footer-faq" className="hover:text-white/70 transition-colors">{t("land_faq")}</Link>
        <span className="opacity-30">·</span>
        <Link to="/auth" data-testid="land-login" className="hover:text-white/70 transition-colors">{t("login")}</Link>
      </footer>
    </div>
  );
}

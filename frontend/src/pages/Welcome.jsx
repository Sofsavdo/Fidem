import React from "react";
import { useNavigate } from "react-router-dom";
import { Heart, Check, Sparkles, ShieldCheck, Users } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import Logo, { LogoBadge } from "@/components/Logo";
import LangSwitch from "@/components/LangSwitch";

export default function Welcome() {
  const { t, user } = useApp();
  const nav = useNavigate();

  const start = () => {
    try { localStorage.setItem("fidem_welcomed", "1"); } catch { /* ignore */ }
    nav(user ? "/onboarding" : "/auth");
  };

  const trust = [
    { Icon: ShieldCheck, label: t("land_trust1_t") },
    { Icon: Users, label: t("land_trust2_t") },
    { Icon: Sparkles, label: t("land_trust3_t") },
  ];

  return (
    <div className="relative h-[100dvh] bg-ink text-white overflow-hidden flex flex-col">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="orb orb-1 opacity-40" />
        <div className="orb orb-2 opacity-25" />
        <div className="orb orb-3 opacity-25" />
      </div>

      <header className="relative z-10 flex items-center justify-between px-5 pt-4 shrink-0">
        <div className="flex items-center gap-2">
          <Logo tone="white" className="w-8 h-8" />
          <span className="font-heading font-bold text-lg tracking-tight">FIDEM</span>
        </div>
        <LangSwitch />
      </header>

      <main className="relative z-10 flex-1 min-h-0 flex flex-col justify-center px-6 max-w-md mx-auto w-full text-center">
        {/* Illustration hero — branded scene: the animated mark on a glowing
            panel with floating hearts. No photo needed, renders instantly. */}
        <div className="relative mx-auto w-full max-w-[280px] aspect-[5/4] rounded-[2rem] bg-gradient-to-br from-primary/25 via-secondary/15 to-transparent border border-white/10 grid place-items-center overflow-hidden">
          <div className="absolute inset-0 bg-grain opacity-[0.15]" />
          <Heart className="absolute top-5 left-6 w-5 h-5 text-primary/70" fill="currentColor" />
          <Heart className="absolute bottom-6 right-7 w-7 h-7 text-secondary/70" fill="currentColor" />
          <Heart className="absolute top-8 right-10 w-3.5 h-3.5 text-gold/80" fill="currentColor" />
          <Sparkles className="absolute bottom-8 left-8 w-4 h-4 text-gold/80" />
          <LogoBadge animated className="w-24 h-24 relative" />
        </div>

        <h1 className="mt-6 font-heading text-3xl sm:text-4xl font-bold leading-[1.1] tracking-tight">
          {t("land_hero_a")}<span className="text-gold">{t("land_hero_em")}</span>{t("land_hero_b")}
        </h1>
        <p className="mt-2.5 text-white/65 text-sm leading-relaxed max-w-sm mx-auto">
          {t("land_subtitle")}
        </p>

        <div className="mt-4 flex items-center justify-center gap-2 flex-wrap">
          {trust.map((it, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 rounded-full bg-white/[0.06] border border-white/10">
              <it.Icon className="w-3.5 h-3.5 text-gold" /> {it.label}
            </span>
          ))}
        </div>

        <button
          onClick={start}
          data-testid="land-cta-primary"
          className="mt-6 w-full rounded-2xl bg-gradient-to-r from-[#F0269D] to-[#8A2BE2] text-white font-semibold text-base py-4 shadow-lg shadow-primary/30 hover:-translate-y-0.5 active:scale-[0.98] transition inline-flex items-center justify-center gap-2"
        >
          <Check className="w-5 h-5" /> {t("welcome_cta_primary")}
        </button>
        <p className="mt-3 text-xs text-white/45">{t("land_social_proof")}</p>
      </main>

      <footer className="relative z-10 text-center text-[11px] text-white/35 pb-5 px-6 flex items-center justify-center gap-4 shrink-0">
        <button onClick={() => nav("/about")} className="hover:text-white/70 transition-colors" data-testid="footer-about">{t("land_about")}</button>
        <span className="opacity-30">·</span>
        <button onClick={() => nav("/faq")} className="hover:text-white/70 transition-colors" data-testid="footer-faq">{t("land_faq")}</button>
        <span className="opacity-30">·</span>
        <button onClick={() => nav("/auth")} className="hover:text-white/70 transition-colors" data-testid="land-login">{t("login")}</button>
      </footer>
    </div>
  );
}

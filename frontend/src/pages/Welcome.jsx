import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ShieldCheck, Sparkles, Heart } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import Logo from "@/components/Logo";
import HeroScene from "@/components/HeroScene";
import LangSwitch from "@/components/LangSwitch";

export default function Welcome() {
  const { t, user } = useApp();
  const nav = useNavigate();

  const start = () => {
    try { localStorage.setItem("fidem_welcomed", "1"); } catch { /* ignore */ }
    nav(user ? "/onboarding" : "/auth");
  };

  const chips = [
    { Icon: ShieldCheck, label: t("land_trust1_t") },
    { Icon: Heart, label: t("land_trust3_t") },
    { Icon: Sparkles, label: t("land_trust2_t") },
  ];

  return (
    <div className="relative h-[100dvh] bg-ink text-white overflow-hidden flex flex-col">
      {/* ---- Hero (top ~56%): couple-at-sunset scene; a real photo dropped at
           public/welcome-hero.jpg automatically replaces the illustration ---- */}
      <div className="relative flex-1 min-h-0">
        <HeroScene className="absolute inset-0" />
        {/* legibility for the text card below */}
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-black/15" />

        {/* top bar over the photo */}
        <div className="relative z-10 flex items-center justify-between px-5 pt-4">
          <div className="flex items-center gap-2">
            <Logo tone="white" className="w-8 h-8 drop-shadow" />
            <span className="font-heading font-bold text-lg tracking-tight drop-shadow">FIDEM</span>
          </div>
          <LangSwitch />
        </div>

        {/* floating chips, like the reference */}
        <div className="absolute z-10 left-5 top-24 flex flex-col gap-2 items-start">
          {chips.map((c, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-white/90 text-ink shadow-lg backdrop-blur"
              style={{ marginLeft: i === 1 ? "3.5rem" : i === 2 ? "1.5rem" : 0 }}
            >
              <c.Icon className="w-3.5 h-3.5 text-primary" /> {c.label}
            </span>
          ))}
        </div>
      </div>

      {/* ---- Text + CTA card (bottom) ---- */}
      <div className="relative z-10 shrink-0 px-6 pb-6 pt-2 -mt-6">
        <div className="rounded-3xl bg-ink/60 backdrop-blur-xl border border-white/10 p-5 text-center">
          <h1 className="font-heading text-2xl sm:text-3xl font-bold leading-tight tracking-tight">
            {t("land_hero_a")}<span className="text-gold">{t("land_hero_em")}</span>{t("land_hero_b")}
          </h1>
          <p className="mt-2 text-white/70 text-sm leading-relaxed">{t("land_subtitle")}</p>

          <button
            onClick={start}
            data-testid="land-cta-primary"
            className="mt-4 w-full rounded-2xl bg-gradient-to-r from-[#F0269D] to-[#8A2BE2] text-white font-semibold text-base py-4 shadow-lg shadow-primary/30 active:scale-[0.98] transition inline-flex items-center justify-center gap-2"
          >
            {t("welcome_cta_primary")} <ArrowRight className="w-5 h-5" />
          </button>

          <div className="mt-3 flex items-center justify-center gap-4 text-[11px] text-white/45">
            <button onClick={() => nav("/about")} data-testid="footer-about" className="hover:text-white/80">{t("land_about")}</button>
            <span className="opacity-30">·</span>
            <button onClick={() => nav("/faq")} data-testid="footer-faq" className="hover:text-white/80">{t("land_faq")}</button>
            <span className="opacity-30">·</span>
            <button onClick={() => nav("/auth")} data-testid="land-login" className="hover:text-white/80">{t("login")}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

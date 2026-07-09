import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ShieldCheck, Sparkles, Heart } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import Logo from "@/components/Logo";
import LangSwitch from "@/components/LangSwitch";

// Hero photo. A bundled file at public/welcome-hero.jpg (drop one in to fully
// control it) takes priority; otherwise a neutral, ethnicity-agnostic romantic
// image (a couple silhouette at sunset — no visible skin tone, culturally safe)
// loads from the CDN. If neither loads, the brand gradient shows.
const HERO_LOCAL = "/welcome-hero.jpg";
const HERO_CDN =
  "https://images.unsplash.com/photo-1508672019048-805c876b67e2?w=1000&q=70&auto=format&fit=crop";

export default function Welcome() {
  const { t, user } = useApp();
  const nav = useNavigate();
  // Try the bundled photo first, fall back to the CDN, then to the gradient.
  const [src, setSrc] = useState(HERO_LOCAL);
  const [imgOk, setImgOk] = useState(true);
  const onImgError = () => {
    if (src === HERO_LOCAL) setSrc(HERO_CDN);
    else setImgOk(false);
  };

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
      {/* ---- Hero photo (top ~56%) ---- */}
      <div className="relative flex-1 min-h-0">
        <div className="absolute inset-0 bg-gradient-to-br from-[#F0269D] via-[#B0279E] to-[#8A2BE2]" />
        {imgOk && (
          <img
            src={src}
            alt=""
            onError={onImgError}
            className="absolute inset-0 w-full h-full object-cover"
          />
        )}
        {/* legibility + brand tint */}
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/30 to-black/25" />

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

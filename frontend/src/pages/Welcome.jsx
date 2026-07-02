import React from "react";
import { Link } from "react-router-dom";
import { Heart, Shield, Users, Sparkles, Crown, Star, ChevronRight, Gift, MessageCircle, ScanFace } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import LangSwitch from "@/components/LangSwitch";

const IMG = {
  hero: "https://images.unsplash.com/photo-1519307212971-dd9561667ffb?w=1100&q=80&auto=format&fit=crop",
  trust: "https://images.unsplash.com/photo-1500662434123-4d06b56a762f?w=1400&q=80&auto=format&fit=crop",
  t1: "https://images.pexels.com/photos/26990489/pexels-photo-26990489.jpeg?auto=compress&cs=tinysrgb&w=200",
  t2: "https://images.unsplash.com/photo-1574740637579-9ca0a610e491?w=200&q=80&auto=format&fit=crop",
  t3: "https://images.unsplash.com/photo-1728368686380-acaca58a5e76?w=200&q=80&auto=format&fit=crop",
};

export default function Welcome() {
  const { t } = useApp();

  const trustBadges = [
    { icon: Shield, t: "land_trust1_t", s: "land_trust1_s" },
    { icon: Users, t: "land_trust2_t", s: "land_trust2_s" },
    { icon: Sparkles, t: "land_trust3_t", s: "land_trust3_s" },
  ];

  const features = [
    { icon: ScanFace, t: "land_f1_t", d: "land_f1_d", color: "primary" },
    { icon: Users, t: "land_f2_t", d: "land_f2_d", color: "secondary" },
    { icon: Sparkles, t: "land_f3_t", d: "land_f3_d", color: "gold" },
    { icon: Crown, t: "land_f4_t", d: "land_f4_d", color: "primary" },
    { icon: Gift, t: "land_f5_t", d: "land_f5_d", color: "secondary" },
    { icon: MessageCircle, t: "land_f6_t", d: "land_f6_d", color: "gold" },
  ];
  const colorMap = {
    primary: { bg: "bg-primary/10", text: "text-primary" },
    secondary: { bg: "bg-secondary/10", text: "text-secondary" },
    gold: { bg: "bg-gold/10", text: "text-gold-dark" },
  };

  const testimonials = [
    { key: "land_test1", name: "Aziza & Bobur", img: IMG.t1 },
    { key: "land_test2", name: "Dilnoza & Sardor", img: IMG.t2 },
    { key: "land_test3", name: "Madina & Diyor", img: IMG.t3 },
  ];

  return (
    <div className="min-h-screen bg-background bg-grain">
      {/* Top nav */}
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary grid place-items-center text-white">
            <Heart className="w-5 h-5" fill="currentColor" />
          </div>
          <span className="font-heading font-bold text-xl">FIDEM</span>
        </div>
        <div className="flex items-center gap-2">
          <LangSwitch />
          <Link to="/auth" data-testid="land-login" className="text-sm font-medium px-4 py-2 rounded-full bg-primary text-white">
            {t("login")}
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-14">
        {/* Hero */}
        <section className="grid md:grid-cols-2 gap-8 items-center">
          <div className="text-center md:text-left space-y-4 order-2 md:order-1">
            <div className="inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-primary/10 text-foreground border border-primary/30">
              <Sparkles className="w-3.5 h-3.5" /> {t("land_badge")}
            </div>
            <h1 className="text-4xl sm:text-5xl font-heading font-bold leading-tight">
              {t("land_hero_a")}<span className="text-primary">{t("land_hero_em")}</span>{t("land_hero_b")}
            </h1>
            <p className="text-lg text-muted-foreground max-w-md mx-auto md:mx-0">
              {t("land_subtitle")}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center md:justify-start pt-2">
              <Link to="/auth" data-testid="land-cta-primary" className="px-6 py-3.5 rounded-2xl bg-primary text-white font-medium text-base shadow-lg">
                {t("welcome_cta_primary")} →
              </Link>
              <a href="#features" className="px-6 py-3.5 rounded-2xl border-2 border-border text-base font-medium">
                {t("welcome_features")}
              </a>
            </div>
            <p className="text-xs text-muted-foreground pt-4">{t("land_social_proof")}</p>
          </div>
          <div className="order-1 md:order-2 relative">
            <div className="relative rounded-[2rem] overflow-hidden shadow-2xl aspect-[4/5] sm:aspect-[3/4] md:aspect-[4/5]">
              <img
                src={IMG.hero}
                alt="FIDEM couple"
                loading="eager"
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-foreground/30 via-transparent to-transparent" />
            </div>
            <div className="absolute -bottom-4 -left-2 sm:left-4 glass rounded-2xl px-4 py-2.5 border border-border/60 shadow-lg flex items-center gap-2">
              <Heart className="w-5 h-5 text-foreground" fill="currentColor" />
              <div className="leading-tight">
                <p className="text-sm font-semibold">{t("land_badge_users") || "Verified members"}</p>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide">FIDEM</p>
              </div>
            </div>
          </div>
        </section>

        {/* Trust badges */}
        <section className="grid grid-cols-3 gap-3 text-center">
          {trustBadges.map((b, i) => (
            <div key={i} className="rounded-2xl border border-border bg-card p-3">
              <b.icon className="w-6 h-6 mx-auto text-foreground" />
              <p className="text-sm font-medium mt-2">{t(b.t)}</p>
              <p className="text-[11px] text-muted-foreground">{t(b.s)}</p>
            </div>
          ))}
        </section>

        {/* Features */}
        <section id="features" className="space-y-4">
          <h2 className="text-2xl font-heading font-semibold text-center">{t("welcome_why")}</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {features.map((f, i) => {
              const c = colorMap[f.color] || colorMap.primary;
              return (
                <div key={i} className="rounded-2xl border border-border bg-card p-4 flex gap-3">
                  <div className={`w-10 h-10 rounded-xl ${c.bg} grid place-items-center shrink-0`}>
                    <f.icon className={`w-5 h-5 ${c.text}`} />
                  </div>
                  <div>
                    <p className="font-semibold">{t(f.t)}</p>
                    <p className="text-sm text-muted-foreground mt-0.5">{t(f.d)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Trust / safety visual band */}
        <section className="relative rounded-3xl overflow-hidden min-h-[260px] flex items-center">
          <img src={IMG.trust} alt="Trust" loading="lazy" className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-foreground/80 via-foreground/55 to-foreground/20" />
          <div className="relative p-7 sm:p-10 max-w-md text-background space-y-3">
            <Shield className="w-8 h-8" />
            <h2 className="text-2xl font-heading font-semibold">{t("land_trust2_t")} · {t("land_trust1_t")}</h2>
            <p className="text-sm opacity-90">{t("land_f2_d")}</p>
          </div>
        </section>

        {/* Pricing teaser */}
        <section className="rounded-3xl bg-gradient-to-br from-primary/10 via-secondary/5 to-gold-light/30 border border-border p-5 text-center space-y-3">
          <h2 className="text-2xl font-heading font-semibold">{t("welcome_pricing")}</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">{t("land_pricing_sub")}</p>
          <div className="grid grid-cols-3 gap-2 pt-2 max-w-md mx-auto">
            <div className="rounded-2xl border border-border bg-card p-3">
              <p className="text-xs text-muted-foreground">FREE</p>
              <p className="font-heading font-semibold mt-1">0 {t("sum")}</p>
            </div>
            <div className="rounded-2xl border-2 border-primary bg-card p-3 relative">
              <p className="text-xs text-foreground">PREMIUM</p>
              <p className="font-heading font-semibold mt-1">79K</p>
            </div>
            <div className="rounded-2xl border border-gold/40 bg-card p-3">
              <p className="text-xs text-gold-dark">VIP 👑</p>
              <p className="font-heading font-semibold mt-1">199K</p>
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section className="space-y-3">
          <h2 className="text-xl font-heading font-semibold text-center">{t("welcome_stories")}</h2>
          <div className="grid sm:grid-cols-3 gap-3">
            {testimonials.map((s, i) => (
              <div key={i} className="rounded-2xl border border-border bg-card p-4 space-y-3">
                <div className="flex items-center gap-1 text-gold-dark">
                  {[0, 1, 2, 3, 4].map((n) => (
                    <Star key={n} className="w-3.5 h-3.5 fill-current" />
                  ))}
                </div>
                <p className="text-sm italic">“{t(s.key)}”</p>
                <div className="flex items-center gap-2 pt-1">
                  <img src={s.img} alt={s.name} loading="lazy" className="w-8 h-8 rounded-full object-cover" />
                  <span className="text-xs font-medium text-muted-foreground">{s.name}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Final CTA */}
        <section className="rounded-3xl bg-foreground text-background p-6 sm:p-8 text-center space-y-3">
          <h2 className="text-2xl font-heading font-semibold">{t("welcome_today")}</h2>
          <p className="text-sm opacity-80">{t("land_final_sub")}</p>
          <Link to="/auth" data-testid="land-cta-final" className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-primary text-white font-medium">
            {t("land_register")} <ChevronRight className="w-4 h-4" />
          </Link>
        </section>

        <footer className="text-center text-xs text-muted-foreground pt-4 pb-8 space-y-1">
          <p>© 2025 FIDEM</p>
          <p>✨ {t("land_footer_tag")}</p>
          <div className="flex justify-center gap-4 pt-3">
            <Link to="/about" data-testid="footer-about" className="hover:text-foreground">{t("land_about")}</Link>
            <Link to="/faq" data-testid="footer-faq" className="hover:text-foreground">{t("land_faq")}</Link>
            <Link to="/auth" className="hover:text-foreground">{t("land_signin")}</Link>
          </div>
        </footer>
      </main>
    </div>
  );
}

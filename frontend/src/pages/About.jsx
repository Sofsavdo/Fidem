import React from "react";
import { Link } from "react-router-dom";
import { Heart, ChevronLeft, Sparkles, Shield, Brain, MessageCircle } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

export default function About() {
  const { t } = useApp();
  return (
    <div className="min-h-screen bg-background bg-grain">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/welcome" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="about-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-secondary grid place-items-center text-white">
            <Heart className="w-4 h-4" fill="currentColor" />
          </div>
          <span className="font-heading font-bold text-lg">{t("about_title")}</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-8">
        <section className="space-y-3">
          <div className="inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-primary/10 text-foreground border border-primary/30">
            <Sparkles className="w-3.5 h-3.5" /> {t("about_mission")}
          </div>
          <h1 className="text-3xl font-heading font-bold leading-tight">
            {t("about_hero")}
          </h1>
          <p className="text-muted-foreground">
            {t("land_subtitle")}
          </p>
        </section>

        <section className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { icon: Shield, title: t("land_f2_t"), text: t("land_f2_d") },
            { icon: Brain, title: t("land_f3_t"), text: t("land_f3_d") },
            { icon: Sparkles, title: t("land_f4_t"), text: t("land_f4_d") },
            { icon: MessageCircle, title: t("land_f6_t"), text: t("land_f6_d") },
          ].map((b, i) => (
            <div key={i} className="rounded-2xl border border-border bg-card p-4">
              <b.icon className="w-5 h-5 text-primary mb-2" />
              <p className="font-semibold">{b.title}</p>
              <p className="text-sm text-muted-foreground mt-1">{b.text}</p>
            </div>
          ))}
        </section>

        <section className="rounded-3xl bg-gradient-to-br from-primary/10 via-secondary/5 to-gold-light/30 border border-border p-5 text-center space-y-3">
          <h2 className="text-2xl font-heading font-semibold">{t("welcome_today")}</h2>
          <p className="text-sm text-muted-foreground">{t("land_final_sub")}</p>
          <Link to="/auth" data-testid="about-cta" className="inline-flex px-6 py-3 rounded-2xl bg-primary text-white font-medium">
            {t("register_now")} →
          </Link>
        </section>

        <footer className="text-center text-xs text-muted-foreground pt-4 pb-8 space-y-1">
          <p>© 2025 FIDEM</p>
          <div className="flex justify-center gap-3 pt-1">
            <Link to="/welcome" className="hover:text-foreground">{t("home")}</Link>
            <Link to="/faq" className="hover:text-foreground">FAQ</Link>
            <Link to="/about" className="hover:text-foreground">{t("about_title")}</Link>
          </div>
        </footer>
      </main>
    </div>
  );
}

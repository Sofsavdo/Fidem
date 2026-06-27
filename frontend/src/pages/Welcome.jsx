import React from "react";
import { Link } from "react-router-dom";
import { Heart, Shield, Users, Sparkles, Crown, Star, ChevronRight, Gift, MessageCircle, ScanFace } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

export default function Welcome() {
  const { t, lang, setLang } = useApp();
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
          <button
            data-testid="welcome-lang"
            onClick={() => {
              const order = ["uz", "ru", "en"];
              setLang(order[(order.indexOf(lang) + 1) % 3]);
            }}
            className="px-2.5 py-1.5 rounded-full bg-muted text-xs font-medium uppercase"
          >
            {lang}
          </button>
          <Link to="/auth" data-testid="land-login" className="text-sm font-medium px-4 py-2 rounded-full bg-primary text-white">
            {t("login")}
          </Link>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-12">
        {/* Hero */}
        <section className="text-center space-y-4">
          <div className="inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-primary/10 text-primary border border-primary/30">
            <Sparkles className="w-3.5 h-3.5" /> Halal tanishuv platformasi #1
          </div>
          <h1 className="text-4xl sm:text-5xl font-heading font-bold leading-tight">
            Hayotingizning <span className="text-primary">to'g'ri yarmini</span> xavfsiz toping
          </h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            FIDEM — oilaviy qadriyatlar bilan, Wali (sovchi) kuzatuvi ostida, AI bilan moslashtirilgan musulmon tanishuv platformasi.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
            <Link to="/auth" data-testid="land-cta-primary" className="px-6 py-3.5 rounded-2xl bg-primary text-white font-medium text-base shadow-lg">
              {t("welcome_cta_primary")} →
            </Link>
            <a href="#features" className="px-6 py-3.5 rounded-2xl border-2 border-border text-base font-medium">
              {t("welcome_features")}
            </a>
          </div>
          <p className="text-xs text-muted-foreground pt-4">✨ Hozir 1000+ ishtirokchi • 12+ to'y bo'lib o'tdi</p>
        </section>

        {/* Trust badges */}
        <section className="grid grid-cols-3 gap-3 text-center">
          {[
            { icon: Shield, title: "3 darajali", sub: "Verification" },
            { icon: Users, title: "Wali rejim", sub: "Oilaviy kuzatuv" },
            { icon: Sparkles, title: "AI moslashtiruv", sub: "Big 5 + 30 mezon" },
          ].map((b, i) => (
            <div key={i} className="rounded-2xl border border-border bg-card p-3">
              <b.icon className="w-6 h-6 mx-auto text-primary" />
              <p className="text-sm font-medium mt-2">{b.title}</p>
              <p className="text-[11px] text-muted-foreground">{b.sub}</p>
            </div>
          ))}
        </section>

        {/* Features */}
        <section id="features" className="space-y-4">
          <h2 className="text-2xl font-heading font-semibold text-center">Nima uchun FIDEM?</h2>
          <div className="space-y-3">
            {[
              { icon: ScanFace, title: "Privacy-first rasm", desc: "Profilingiz rasmlari blurli, faqat ishonganlarga ochiladi.", color: "primary" },
              { icon: Users, title: "Wali/Sovchi tizimi", desc: "Ota-ona yoki yaqin qarindosh chatlaringizni kuzatib turishi mumkin (read-only).", color: "secondary" },
              { icon: Sparkles, title: "Big 5 shaxsiyat testi", desc: "AI yordamida sizga xarakter, qiziqish, hayotiy maqsad bo'yicha eng mos kishini topadi.", color: "gold" },
              { icon: Crown, title: "Sovchi Concierge", desc: "Premium foydalanuvchilarga 5 ta professional sovchi tanlangan moslar (199K so'm).", color: "primary" },
              { icon: Gift, title: "Halal Sovg'a tizimi", desc: "E'tibor ko'rsatish uchun bepul atirgul yoki maxsus sovg'alar. Olgan kishi cashout qila oladi.", color: "secondary" },
              { icon: MessageCircle, title: "Xavfsiz muloqot", desc: "AI yomon so'z + telefon ulashish blokirovkasi. Family Share — nikoh bosqichida ota-ona telefonlari almashinadi.", color: "gold" },
            ].map((f, i) => {
              const colorMap = {
                primary: { bg: "bg-primary/10", text: "text-primary" },
                secondary: { bg: "bg-secondary/10", text: "text-secondary" },
                gold: { bg: "bg-gold/10", text: "text-gold-dark" },
              };
              const c = colorMap[f.color] || colorMap.primary;
              return (
                <div key={i} className="rounded-2xl border border-border bg-card p-4 flex gap-3">
                  <div className={`w-10 h-10 rounded-xl ${c.bg} grid place-items-center shrink-0`}>
                    <f.icon className={`w-5 h-5 ${c.text}`} />
                  </div>
                  <div>
                    <p className="font-semibold">{f.title}</p>
                    <p className="text-sm text-muted-foreground mt-0.5">{f.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Pricing teaser */}
        <section className="rounded-3xl bg-gradient-to-br from-primary/10 via-secondary/5 to-gold-light/30 border border-border p-5 text-center space-y-3">
          <h2 className="text-2xl font-heading font-semibold">Access bepul, Acceleration pulli</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">Asosiy funksiyalar har doim bepul. To'lov faqat tezroq topish, ko'proq e'tibor olish yoki maxsus xizmat uchun.</p>
          <div className="grid grid-cols-3 gap-2 pt-2">
            <div className="rounded-2xl border border-border bg-card p-3">
              <p className="text-xs text-muted-foreground">FREE</p>
              <p className="font-heading font-semibold mt-1">0 so'm</p>
            </div>
            <div className="rounded-2xl border-2 border-primary bg-card p-3 relative">
              <p className="text-xs text-primary">PREMIUM</p>
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
          <h2 className="text-xl font-heading font-semibold text-center">Muvaffaqiyat hikoyalari</h2>
          {[
            { name: "Aziza & Bobur", text: "3 oy ichida tanishdik, to'y qildik. AI moslashtiruv haqiqatan ishlaydi!" },
            { name: "Dilnoza & Sardor", text: "Wali tizimi otamga ko'rsatib bordim, hammasi shaffof. Rahmat FIDEM!" },
            { name: "Madina & Diyor", text: "Big 5 test natijasi bizni juda yaqinlashtirdi." },
          ].map((s, i) => (
            <div key={i} className="rounded-2xl border border-border bg-card p-4">
              <p className="text-sm italic">“{s.text}”</p>
              <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                <Star className="w-3 h-3 text-gold-dark fill-gold-dark" /><Star className="w-3 h-3 text-gold-dark fill-gold-dark" /><Star className="w-3 h-3 text-gold-dark fill-gold-dark" /><Star className="w-3 h-3 text-gold-dark fill-gold-dark" /><Star className="w-3 h-3 text-gold-dark fill-gold-dark" /> — {s.name}
              </p>
            </div>
          ))}
        </section>

        {/* Final CTA */}
        <section className="rounded-3xl bg-foreground text-background p-6 text-center space-y-3">
          <h2 className="text-2xl font-heading font-semibold">Bugun boshlang</h2>
          <p className="text-sm opacity-80">Profil yaratish bepul • 3 daqiqada tayyor</p>
          <Link to="/auth" data-testid="land-cta-final" className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-primary text-white font-medium">
            Ro'yxatdan o'tish <ChevronRight className="w-4 h-4" />
          </Link>
        </section>

        <footer className="text-center text-xs text-muted-foreground pt-8 pb-4 space-y-1">
          <p>© 2025 FIDEM — Halal Matchmaking</p>
          <p>✨ Sizga mos insonni xavfsiz topishga yordam beramiz</p>
          <div className="flex justify-center gap-4 pt-3">
            <Link to="/about" data-testid="footer-about" className="hover:text-foreground">Biz haqimizda</Link>
            <Link to="/faq" data-testid="footer-faq" className="hover:text-foreground">FAQ</Link>
            <Link to="/auth" className="hover:text-foreground">Kirish</Link>
          </div>
        </footer>
      </main>
    </div>
  );
}

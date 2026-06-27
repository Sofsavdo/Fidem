import React from "react";
import { Link } from "react-router-dom";
import { Heart, ChevronLeft, Sparkles, Shield, Users, MessageCircle } from "lucide-react";

export default function About() {
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
          <span className="font-heading font-bold text-lg">Biz haqimizda</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-8">
        <section className="space-y-3">
          <div className="inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-primary/10 text-primary border border-primary/30">
            <Sparkles className="w-3.5 h-3.5" /> Bizning Missiya
          </div>
          <h1 className="text-3xl font-heading font-bold leading-tight">
            Halal va xavfsiz tanishuv — oilaviy qadriyatlar bilan
          </h1>
          <p className="text-muted-foreground">
            FIDEM — musulmon yoshlari uchun maxsus yaratilgan, oila qadriyatlariga asoslangan tanishuv platformasi. Maqsadimiz — har bir foydalanuvchini xavfsiz, halol va shaffof tarzda hayotining to'g'ri yarmi bilan tanishtirishdir.
          </p>
        </section>

        <section className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { icon: Shield, title: "3 darajali tasdiqlash", text: "Identitet, selfie va moliyaviy holat tasdiqlanadi. Sohta profillarga o'rin yo'q." },
            { icon: Users, title: "Wali (Sovchi) tizimi", text: "Ota-onangiz yoki yaqin qarindosh chatlaringizni read-only tarzda kuzatishi mumkin." },
            { icon: Sparkles, title: "AI moslashtiruv", text: "Big 5 shaxsiyat testi + 30+ mezon bo'yicha eng mos kishini topadi." },
            { icon: MessageCircle, title: "AI muloqot xavfsizligi", text: "Yomon so'z, telefon raqam yoki tashqi havola almashish avtomatik bloklanadi." },
          ].map((b, i) => (
            <div key={i} className="rounded-2xl border border-border bg-card p-4">
              <b.icon className="w-5 h-5 text-primary mb-2" />
              <p className="font-semibold">{b.title}</p>
              <p className="text-sm text-muted-foreground mt-1">{b.text}</p>
            </div>
          ))}
        </section>

        <section className="rounded-3xl border border-border bg-card p-5 space-y-3">
          <h2 className="text-xl font-heading font-semibold">Bizning qadriyatlar</h2>
          <ul className="space-y-2 text-sm">
            <li className="flex gap-2"><span className="text-primary">✓</span><span><b>Shaffoflik</b> — har bir profil tasdiqlangan</span></li>
            <li className="flex gap-2"><span className="text-primary">✓</span><span><b>Oilaviy nazorat</b> — Wali tizimi bilan ota-ona xabardor</span></li>
            <li className="flex gap-2"><span className="text-primary">✓</span><span><b>Halal tarzda</b> — diniy va madaniy qadriyatlarga hurmat</span></li>
            <li className="flex gap-2"><span className="text-primary">✓</span><span><b>Maxfiylik</b> — rasmlar blurli, faqat ishonganlarga ochiladi</span></li>
            <li className="flex gap-2"><span className="text-primary">✓</span><span><b>Real natija</b> — to'y va oila qurish maqsadi</span></li>
          </ul>
        </section>

        <section className="rounded-3xl bg-gradient-to-br from-primary/10 via-secondary/5 to-gold-light/30 border border-border p-5 text-center space-y-3">
          <h2 className="text-2xl font-heading font-semibold">Bizga qo'shiling</h2>
          <p className="text-sm text-muted-foreground">Bepul ro'yxatdan o'ting va birinchi uchrashuvingizni boshlang.</p>
          <Link to="/auth" data-testid="about-cta" className="inline-flex px-6 py-3 rounded-2xl bg-primary text-white font-medium">
            Hozir boshlash →
          </Link>
        </section>

        <footer className="text-center text-xs text-muted-foreground pt-4 pb-8 space-y-1">
          <p>© 2025 FIDEM — Halal Matchmaking</p>
          <div className="flex justify-center gap-3 pt-1">
            <Link to="/welcome" className="hover:text-foreground">Bosh sahifa</Link>
            <Link to="/faq" className="hover:text-foreground">FAQ</Link>
            <Link to="/about" className="hover:text-foreground">Biz haqimizda</Link>
          </div>
        </footer>
      </main>
    </div>
  );
}

import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Heart, ChevronLeft, Plus, Minus } from "lucide-react";

const QA = [
  {
    q: "FIDEM bepulmi?",
    a: "Ha, asosiy funksiyalar bepul: ro'yxatdan o'tish, profil yaratish, kun davomida nomzodlarni ko'rish va xabar yozish. To'lov faqat tezroq topish, ko'proq e'tibor olish yoki maxsus xizmatlar uchun (Premium 79K, VIP 199K, Sovchi Concierge 199K).",
  },
  {
    q: "Wali (Sovchi) tizimi nima?",
    a: "Wali — ota-ona yoki yaqin qarindosh sizning chatlaringizni faqat o'qib tura oladigan tizim. U yozish yoki aralashish huquqiga ega emas, faqat kuzatib turadi. Bu oilaviy ishonchni mustahkamlaydi.",
  },
  {
    q: "Rasmlarim kimga ochiq?",
    a: "Rasmlaringiz boshqalarga blur (xira) holatda ko'rinadi. Faqat siz o'zingiz ochishga ruxsat bergan kishilar ravshan ko'radi. Bu maxfiyligingizni saqlab qoladi.",
  },
  {
    q: "Sovg'a (Gift) tizimi qanday ishlaydi?",
    a: "Sovg'a — kimgadir e'tibor ko'rsatishning halol usuli. 12 ta turdagi sovg'a bor: 2 tasi bepul (haftalik kvotali atirgul va yurakcha), 10 tasi pulli (2,000 so'mdan 499,000 so'mgacha). Sovg'a olgan kishi 50% nominal so'mga aylantirib yechib olishi mumkin.",
  },
  {
    q: "Sovchi Concierge nima?",
    a: "199,000 so'mga 30 kun ichida professional sovchi sizning maqsadingizga eng mos 5 ta kishini qo'lda tanlab beradi. Har bir mos uchun batafsil izoh va tushuntirish berib qo'yiladi.",
  },
  {
    q: "Profilim qanday tasdiqlanadi?",
    a: "3 daraja bor: (1) Identitet — pasport rasmi, (2) Selfie — yuz tekshiruvi, (3) Moliyaviy — daromad/biznes hujjati. Har bir daraja tasdiqlangach, profilingizda mos badge paydo bo'ladi.",
  },
  {
    q: "Tanish bo'lgan kishi telefon raqam bera oladi?",
    a: "Yo'q — chatlarda telefon raqam yoki tashqi havola yozishga ruxsat berilmaydi (AI avtomatik bloklaydi). Oila bosqichida VIP foydalanuvchilar 'Family Share' orqali ota-ona telefonlari bilan almashishlari mumkin.",
  },
  {
    q: "Boshqa viloyatdagi nomzodlarni ko'rishim mumkinmi?",
    a: "Premium yoki VIP foydalanuvchilar Travel Mode orqali 1-30 kun davomida boshqa viloyatdagi nomzodlarni ko'rishlari mumkin. 13 ta O'zbek viloyati qo'llab-quvvatlanadi.",
  },
  {
    q: "Mening ma'lumotlarim xavfsizmi?",
    a: "Ha, butun ma'lumotlar shifrlangan holda saqlanadi. Biz hech qachon ma'lumotlaringizni 3-shaxslarga sotmaymiz. Profil rasmlari shaxsiy server'da xavfsiz saqlanadi.",
  },
  {
    q: "Ro'yxatdan o'tish uchun nima kerak?",
    a: "Telegram orqali (oson) yoki email + parol. Yoshingiz 18+ bo'lishi shart. Ro'yxatdan o'tgandan keyin 7 bosqichli profil yaratishni boshlaysiz (3-5 daqiqa).",
  },
];

export default function FAQ() {
  const [open, setOpen] = useState(null);
  return (
    <div className="min-h-screen bg-background bg-grain">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/welcome" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="faq-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-secondary grid place-items-center text-white">
            <Heart className="w-4 h-4" fill="currentColor" />
          </div>
          <span className="font-heading font-bold text-lg">Tez-tez so'raladigan savollar</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-3">
        <p className="text-center text-sm text-muted-foreground pb-4">Savollaringizga javob topa olmadingizmi? <Link to="/about" className="text-primary underline">Biz bilan bog'laning</Link></p>

        {QA.map((it, i) => (
          <div key={i} className="rounded-2xl border border-border bg-card overflow-hidden" data-testid={`faq-${i}`}>
            <button
              onClick={() => setOpen(open === i ? null : i)}
              className="w-full text-left px-4 py-3 flex items-center justify-between gap-3 hover:bg-muted/30"
            >
              <span className="font-medium text-sm sm:text-base">{it.q}</span>
              {open === i ? <Minus className="w-4 h-4 shrink-0 text-primary" /> : <Plus className="w-4 h-4 shrink-0 text-muted-foreground" />}
            </button>
            {open === i && (
              <div className="px-4 pb-4 text-sm text-muted-foreground border-t border-border/40 pt-3">
                {it.a}
              </div>
            )}
          </div>
        ))}

        <section className="rounded-3xl bg-gradient-to-br from-primary/10 via-secondary/5 to-gold-light/30 border border-border p-5 text-center space-y-3 mt-8">
          <h2 className="text-xl font-heading font-semibold">Hali ham savol bormi?</h2>
          <p className="text-sm text-muted-foreground">Telegram orqali biz bilan bog'laning yoki ilovani sinab ko'ring.</p>
          <Link to="/auth" data-testid="faq-cta" className="inline-flex px-6 py-3 rounded-2xl bg-primary text-white font-medium">
            Ro'yxatdan o'tish
          </Link>
        </section>

        <footer className="text-center text-xs text-muted-foreground pt-4 pb-8 space-y-1">
          <p>© 2025 FIDEM — Halal Matchmaking</p>
          <div className="flex justify-center gap-3 pt-1">
            <Link to="/welcome" className="hover:text-foreground">Bosh sahifa</Link>
            <Link to="/about" className="hover:text-foreground">Biz haqimizda</Link>
          </div>
        </footer>
      </main>
    </div>
  );
}

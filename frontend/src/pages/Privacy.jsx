import React from "react";
import { ChevronLeft, ShieldCheck } from "lucide-react";

// Legal document - Uzbek-only, same reasoning as Terms.jsx.

function S({ n, title, children }) {
  return (
    <section className="space-y-2">
      <h2 className="font-heading text-base font-semibold">{n}. {title}</h2>
      <div className="text-sm text-muted-foreground leading-relaxed space-y-2">{children}</div>
    </section>
  );
}

export default function Privacy() {
  return (
    <div className="min-h-[100dvh] bg-background">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <button type="button" onClick={() => window.history.back()} className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="privacy-back">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-heading font-semibold text-lg flex items-center gap-2"><ShieldCheck className="w-4 h-4" /> Maxfiylik siyosati</span>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-6 space-y-6 pb-16" data-testid="privacy-page">
        <p className="text-xs text-muted-foreground">Versiya 1.0 · FIDEM ma'lumotlaringizga jiddiy munosabatda bo'ladi</p>

        <S n="1" title="Qanday ma'lumotlar yig'iladi">
          <ul className="list-disc pl-5 space-y-1">
            <li>Profil ma'lumotlari: ism, yosh, jins, hudud, ma'lumoti, kasbi, bio va qidiruv afzalliklari;</li>
            <li>Profil rasmi;</li>
            <li>Telegram identifikatori (Telegram orqali kirilganda);</li>
            <li>Ilova ichidagi faoliyat: ko'rishlar, yoqtirishlar, xabarlar, to'lovlar tarixi;</li>
            <li>Ixtiyoriy joylashuv tasdig'i (faqat siz ruxsat bersangiz; aniq koordinatalar boshqa foydalanuvchilarga hech qachon ko'rsatilmaydi).</li>
          </ul>
        </S>

        <S n="2" title="Ma'lumotlardan foydalanish maqsadi">
          <p>Ma'lumotlar faqat xizmatni ko'rsatish uchun ishlatiladi: mos nomzodlarni tanlash, xavfsizlikni ta'minlash, to'lovlarni qayta ishlash va qo'llab-quvvatlash. Ma'lumotlaringiz uchinchi shaxslarga SOTILMAYDI.</p>
        </S>

        <S n="3" title="To'lov ma'lumotlari">
          <p>To'lovlar CLICK tizimi orqali amalga oshiriladi. Plastik karta raqamingiz va boshqa to'lov rekvizitlaringiz FIDEM serverlarida saqlanmaydi — ular faqat CLICK tomonida qayta ishlanadi. Yechib olish uchun kiritilgan karta raqami faqat pul o'tkazish maqsadida ishlatiladi.</p>
        </S>

        <S n="4" title="Uchinchi tomon xizmatlari">
          <ul className="list-disc pl-5 space-y-1">
            <li>CLICK — to'lovlarni qayta ishlash;</li>
            <li>Telegram — autentifikatsiya va bildirishnomalar;</li>
            <li>AI rasm tekshiruvi — profil rasmi haqiqiy inson yuzi ekanini tekshirish (rasm faqat tekshiruv uchun yuboriladi, o'qitish uchun ishlatilmaydi);</li>
            <li>Texnik analitika va xatolik kuzatuvi (shaxsiy yozishmalar mazmuni yuborilmaydi).</li>
          </ul>
        </S>

        <S n="5" title="Rasm va profil himoyasi">
          <p>Yopiq rasmlar faqat siz ruxsat bergan foydalanuvchilarga ko'rsatiladi va serverdan ruxsatsiz uzatilmaydi. Ilova ichida rasmlarni saqlab olish va ulashish funksiyalari cheklangan. Maxfiy rejim yoqilganda profilingiz qidiruv va ro'yxatlarda ko'rinmaydi.</p>
        </S>

        <S n="6" title="Saqlash muddati va o'chirish">
          <p>Ma'lumotlar akkaunt faol bo'lgan davrda saqlanadi. Akkauntni va unga bog'liq ma'lumotlarni o'chirishni so'rash uchun qo'llab-quvvatlashga murojaat qiling: <a className="text-primary underline" href="https://t.me/FidemAppSupport" target="_blank" rel="noreferrer">t.me/FidemAppSupport</a></p>
        </S>

        <S n="7" title="Rozilik">
          <p>Ro'yxatdan o'tishda rozilik belgisini qo'yish orqali siz ushbu siyosatga muvofiq ma'lumotlaringiz qayta ishlanishiga rozilik bildirasiz. Siyosat yangilanishi mumkin; muhim o'zgarishlarda xabardor qilinasiz.</p>
        </S>
      </main>
    </div>
  );
}

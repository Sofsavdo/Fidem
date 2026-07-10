import React from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, FileText } from "lucide-react";

// Legal document - deliberately Uzbek-only (the platform's audience and the
// language users actually consent in). Version bumps must also bump
// terms_version in backend/routers/auth_r.py so re-consent can be required.
export const TERMS_VERSION = "1.0";

function S({ n, title, children }) {
  return (
    <section className="space-y-2">
      <h2 className="font-heading text-base font-semibold">{n}. {title}</h2>
      <div className="text-sm text-muted-foreground leading-relaxed space-y-2">{children}</div>
    </section>
  );
}

export default function Terms() {
  return (
    <div className="min-h-[100dvh] bg-background">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <button type="button" onClick={() => window.history.back()} className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="terms-back">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-heading font-semibold text-lg flex items-center gap-2"><FileText className="w-4 h-4" /> Foydalanish shartlari</span>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-6 space-y-6 pb-16" data-testid="terms-page">
        <p className="text-xs text-muted-foreground">
          Versiya {TERMS_VERSION} · FIDEM — jiddiy tanishuv va oila qurish platformasi ·{" "}
          <Link to="/privacy" className="text-primary underline">Maxfiylik siyosati</Link>
        </p>

        <S n="1" title="Umumiy qoidalar">
          <p>FIDEM — jiddiy niyatdagi insonlar uchun tanishuv platformasi. Ilovadan faqat 18 yoshga to'lgan shaxslar foydalanishi mumkin.</p>
          <p>Ro'yxatdan o'tishda rozilik belgilarini (galochka) qo'yish — ushbu shartlarni o'qib chiqqaningiz, tushunganingiz va ularga TO'LIQ ROZILIK bildirganingizni tasdiqlovchi elektron imzo hisoblanadi. Rozilik sanasi va shartlar versiyasi tizimda saqlanadi.</p>
        </S>

        <S n="2" title="Profil va haqqoniylik">
          <p>Foydalanuvchi o'zi haqida haqqoniy ma'lumot kiritish, o'z rasmini joylash va bir kishiga bitta profil qoidasiga rioya qilish majburiyatini oladi. Profil rasmlari tekshiruvdan o'tadi; soxta, boshqa shaxsga tegishli yoki qoidalarga zid rasmlar rad etiladi.</p>
        </S>

        <S n="3" title="To'lovlar va tariflar">
          <p>Tarif to'lovlari IXTIYORIY tanlanadi va qo'shimcha imkoniyatlar beradi. Barcha to'lovlar CLICK to'lov tizimi orqali avtomatik amalga oshiriladi.</p>
          <p className="font-medium text-foreground">Tarif aktivatsiya qilingandan so'ng to'langan pul QAYTARILMAYDI.</p>
          <p>Ilova ichidagi balans faqat ilova ichidagi xizmatlar uchun ishlatiladi va naqd pulga yechib olinmaydi. Yechib olish faqat referal daromadiga tegishli (4-band).</p>
        </S>

        <S n="4" title="Referal dasturi va to'lovlar tartibi">
          <p>Referal daromadi — platforma rivojiga qo'shgan hissangiz uchun BONUS tariqasida ixtiyoriy ajratiladigan mablag'. U kafolatlangan ish haqi yoki majburiy to'lov emas.</p>
          <p>To'lab berish tartibi:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Faqat administrator TASDIQLAGAN qismgina to'lab beriladi;</li>
            <li>Daromad avval "hold" (kutish) holatida turadi va shu muddat tugagandan so'ng yechishga ochiladi;</li>
            <li>Yechib olish so'rovi yuborilgan kundan boshlab 5 (besh) bank ish kuni ichida to'lab beriladi;</li>
            <li>Administrator qoidabuzarlik yoki firibgarlikdan shubhalansa, so'rovni RAD ETISH, bekor qilish va shubhali yo'l bilan yig'ilgan balansni ANNULATSIYA QILISH (kuydirish) huquqiga ega.</li>
          </ul>
        </S>

        <S n="5" title="Odob-axloq, diniy va siyosiy neytrallik">
          <p>Platformada o'zaro hurmat majburiy. Haqorat, kamsitish, behayo kontent taqiqlanadi.</p>
          <p>FIDEM diniy va siyosiy masalalarda NEYTRAL platforma. Davlatga yoki siyosiy vaziyatlarga qarshi fikrlar tarqatish, diniy yoki siyosiy targ'ibot olib borish taqiqlanadi. Bunday holatlarda foydalanuvchi ogohlantirishsiz BLOKLANADI.</p>
        </S>

        <S n="6" title="Muloqot xavfsizligi — foydalanuvchining o'z javobgarligi">
          <p className="font-medium text-foreground">Chatdagi muloqot xavfsizligi har bir foydalanuvchining O'Z ZIMMASIDA. Ilova foydalanuvchilar o'rtasidagi yozishmalar oqibatlariga javob bermaydi.</p>
          <p>Qat'iyan tavsiya etiladi va foydalanuvchi o'z javobgarligini tan oladi:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Suhbatdoshga shaxsni tasdiqlovchi hujjat, pasport, plastik karta ma'lumotlari va ochiq (intim) rasmlarni YUBORMASLIK;</li>
            <li>Pul so'rash, tovlamachilik, shantaj va boshqa firibgarlik holatlariga uchraganda — bu uchun jabrlanuvchining o'zi javobgar bo'lib, ilova yetkazilgan zararni QOPLAB BERMAYDI;</li>
            <li>Bunday holatlarda ilovadagi SHIKOYAT QILISH va BLOKLASH funksiyalaridan darhol foydalanish kerak.</li>
          </ul>
          <p>Platforma o'z navbatida bunday noinsof foydalanuvchilarga qarshi kurashadi — ularni bloklash va ilovadan chiqarib yuborishga harakat qiladi, lekin jabrlanganlarning zararini qoplash majburiyatini olmaydi.</p>
        </S>

        <S n="7" title="Javobgarlik cheklovi">
          <p>Xizmat "boricha" (as is) taqdim etiladi. Platforma tanishuvlar natijasini, turmush qurishni yoki muayyan foydalanuvchi bilan muloqotni kafolatlamaydi va foydalanuvchilar o'rtasidagi shaxsiy kelishmovchiliklarga aralashmaydi.</p>
        </S>

        <S n="8" title="Bloklash">
          <p>Qoidalar buzilganda platforma profilni ogohlantirishsiz cheklash, bloklash yoki o'chirish huquqiga ega. Bloklangan foydalanuvchining to'lovlari qaytarilmaydi.</p>
        </S>

        <S n="9" title="O'zgartirishlar va aloqa">
          <p>Shartlar yangilanishi mumkin; muhim o'zgarishlarda qayta rozilik so'raladi. Savollar uchun: <a className="text-primary underline" href="https://t.me/FidemAppSupport" target="_blank" rel="noreferrer">t.me/FidemAppSupport</a></p>
        </S>
      </main>
    </div>
  );
}

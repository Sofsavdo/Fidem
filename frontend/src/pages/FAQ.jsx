import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Plus, Minus } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import Logo from "@/components/Logo";

const QA_BY_LANG = {
  uz: [
    { q: "FIDEM bepulmi?", a: "Asosiy funksiyalar bepul. Premium (79K), VIP (199K) va Concierge (199K) — qo'shimcha xizmatlar uchun." },
    { q: "Rasmlarim kimga ko'rinadi?", a: "Rasmlar boshqalarga xira (blur) holatda ko'rinadi. Faqat siz ruxsat bergan kishilarga aniq ko'rinadi." },
    { q: "Profil qanday tasdiqlanadi?", a: "3 daraja: Identitet (pasport), Selfie (yuz tekshiruvi) va Moliyaviy (daromad hujjati)." },
    { q: "Telefon raqam ulashish mumkinmi?", a: "Chatda taqiqlanadi — AI avtomatik bloklaydi. VIP foydalanuvchilar Family Share orqali ota-ona aloqasi bilan almashishlari mumkin." },
    { q: "Sovg'a tizimi qanday ishlaydi?", a: "12 ta sovg'a: 2 tasi bepul, 10 tasi pulli (2K–499K so'm). Olgan kishi 50%ni so'mga aylantirib yechib oladi." },
    { q: "Concierge nima?", a: "199,000 so'mga 30 kun ichida mutaxassis sizga 5 ta qo'lda tanlangan mos profilni taqdim etadi." },
    { q: "Ma'lumotlarim xavfsizmi?", a: "Ha — shifrlangan, 3-shaxslarga sotilmaydi. Rasmlar shaxsiy serverda saqlanadi." },
    { q: "Yoshim necha bo'lishi kerak?", a: "18+. Yuz tekshiruvi ham yoshingizni tasdiqlaydi." },
  ],
  ru: [
    { q: "FIDEM бесплатный?", a: "Базовые функции бесплатны. Premium (79K), VIP (199K) и Concierge (199K) — дополнительные сервисы." },
    { q: "Кому видны мои фото?", a: "Фото видны другим в размытом виде. Чётко — только тем, кому вы открыли." },
    { q: "Как верифицируется профиль?", a: "3 уровня: Личность (паспорт), Селфи (проверка лица), Финансовая (документ о доходе)." },
    { q: "Можно ли делиться телефоном?", a: "В чате запрещено — AI блокирует. VIP может обменяться через Family Share (родители)." },
    { q: "Как работают подарки?", a: "12 подарков: 2 бесплатные, 10 платные (2K–499K сум). Получатель выводит 50% наличными." },
    { q: "Что такое Concierge?", a: "199K сум — 30 дней, эксперт подбирает 5 профилей вручную." },
    { q: "Безопасны ли мои данные?", a: "Да — шифрование, без продажи третьим лицам. Фото на защищённом сервере." },
    { q: "Какой возраст требуется?", a: "18+. Проверка лица также подтверждает возраст." },
  ],
  en: [
    { q: "Is FIDEM free?", a: "Core features are free. Premium (79K), VIP (199K) and Concierge (199K) are paid add-ons." },
    { q: "Who can see my photos?", a: "Photos appear blurred to others. Only people you allow see them clearly." },
    { q: "How is the profile verified?", a: "3 levels: ID (passport), Selfie (face check), Financial (income proof)." },
    { q: "Can I share my phone number?", a: "Blocked in chat — AI moderates automatically. VIP can exchange via Family Share (parents)." },
    { q: "How do gifts work?", a: "12 gifts: 2 free, 10 paid (2K–499K UZS). Recipients cash out 50%." },
    { q: "What is Concierge?", a: "199K UZS for 30 days — an expert hand-picks 5 matches for you." },
    { q: "Is my data safe?", a: "Yes — encrypted, never sold. Photos on secure storage." },
    { q: "What's the minimum age?", a: "18+. Face check also confirms age." },
  ],
};

export default function FAQ() {
  const { lang, t } = useApp();
  const QA = QA_BY_LANG[lang] || QA_BY_LANG.uz;
  const [open, setOpen] = useState(null);
  return (
    <div className="min-h-screen bg-background bg-grain">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/welcome" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="faq-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-2">
          <Logo className="w-8 h-8" />
          <span className="font-heading font-bold text-lg">FAQ</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-3">
        <p className="text-center text-sm text-muted-foreground pb-4">{t("faq_cta_subtitle")} <Link to="/about" className="text-foreground underline">{t("contact_us")}</Link></p>

        {QA.map((it, i) => (
          <div key={i} className="rounded-2xl border border-border bg-card overflow-hidden" data-testid={`faq-${i}`}>
            <button
              onClick={() => setOpen(open === i ? null : i)}
              className="w-full text-left px-4 py-3 flex items-center justify-between gap-3 hover:bg-muted/30"
            >
              <span className="font-medium text-sm sm:text-base">{it.q}</span>
              {open === i ? <Minus className="w-4 h-4 shrink-0 text-foreground" /> : <Plus className="w-4 h-4 shrink-0 text-muted-foreground" />}
            </button>
            {open === i && (
              <div className="px-4 pb-4 text-sm text-muted-foreground border-t border-border/40 pt-3">
                {it.a}
              </div>
            )}
          </div>
        ))}

        <section className="rounded-3xl bg-gradient-to-br from-primary/10 via-secondary/5 to-gold-light/30 border border-border p-5 text-center space-y-3 mt-8">
          <p className="text-sm text-muted-foreground">{t("land_final_sub")}</p>
          <Link to="/auth" data-testid="faq-cta" className="inline-flex px-6 py-3 rounded-2xl bg-primary text-white font-medium">
            {t("register")}
          </Link>
        </section>

        <footer className="text-center text-xs text-muted-foreground pt-4 pb-8 space-y-1">
          <p>© 2025 FIDEM</p>
          <div className="flex justify-center gap-3 pt-1">
            <Link to="/welcome" className="hover:text-foreground">{t("home")}</Link>
            <Link to="/about" className="hover:text-foreground">{t("about_title")}</Link>
          </div>
        </footer>
      </main>
    </div>
  );
}

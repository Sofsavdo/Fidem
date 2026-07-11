import React from "react";
import { ChevronLeft, ShieldCheck } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

// Privacy policy, localized uz/ru/en (same structure as Terms.jsx).
const P = {
  uz: {
    title: "Maxfiylik siyosati",
    tagline: "FIDEM ma'lumotlaringizga jiddiy munosabatda bo'ladi",
    sections: [
      ["Qanday ma'lumotlar yig'iladi", [
        "Profil ma'lumotlari: ism, yosh, jins, hudud, ma'lumoti, kasbi, bio va qidiruv afzalliklari; profil rasmi; Telegram identifikatori (Telegram orqali kirilganda); ilova ichidagi faoliyat: ko'rishlar, yoqtirishlar, xabarlar, to'lovlar tarixi; ixtiyoriy joylashuv tasdig'i (faqat siz ruxsat bersangiz; aniq koordinatalar boshqa foydalanuvchilarga hech qachon ko'rsatilmaydi).",
      ]],
      ["Foydalanish maqsadi", [
        "Ma'lumotlar faqat xizmatni ko'rsatish uchun ishlatiladi: mos nomzodlarni tanlash, xavfsizlikni ta'minlash, to'lovlarni qayta ishlash va qo'llab-quvvatlash. Ma'lumotlaringiz uchinchi shaxslarga SOTILMAYDI.",
      ]],
      ["To'lov ma'lumotlari", [
        "To'lovlar CLICK tizimi orqali amalga oshiriladi. Plastik karta raqamingiz va boshqa to'lov rekvizitlaringiz FIDEM serverlarida saqlanmaydi — ular faqat CLICK tomonida qayta ishlanadi. Yechib olish uchun kiritilgan karta raqami faqat pul o'tkazish maqsadida ishlatiladi.",
      ]],
      ["Uchinchi tomon xizmatlari", [
        "CLICK — to'lovlarni qayta ishlash; Telegram — autentifikatsiya va bildirishnomalar; AI rasm tekshiruvi — profil rasmi haqiqiy inson yuzi ekanini tekshirish (rasm faqat tekshiruv uchun yuboriladi, o'qitish uchun ishlatilmaydi); texnik analitika va xatolik kuzatuvi (shaxsiy yozishmalar mazmuni yuborilmaydi).",
      ]],
      ["Rasm va profil himoyasi", [
        "Yopiq rasmlar faqat siz ruxsat bergan foydalanuvchilarga ko'rsatiladi va serverdan ruxsatsiz uzatilmaydi. Ilova ichida rasmlarni saqlab olish va ulashish funksiyalari cheklangan. Maxfiy rejim yoqilganda profilingiz qidiruv va ro'yxatlarda ko'rinmaydi.",
      ]],
      ["Saqlash muddati va o'chirish", [
        "Ma'lumotlar akkaunt faol bo'lgan davrda saqlanadi. Akkauntni va unga bog'liq ma'lumotlarni o'chirishni so'rash uchun qo'llab-quvvatlashga murojaat qiling: t.me/FidemAppSupport",
      ]],
      ["Rozilik", [
        "Ro'yxatdan o'tishda rozilik belgisini qo'yish orqali siz ushbu siyosatga muvofiq ma'lumotlaringiz qayta ishlanishiga rozilik bildirasiz. Siyosat yangilanishi mumkin; muhim o'zgarishlarda xabardor qilinasiz.",
      ]],
    ],
  },
  ru: {
    title: "Политика конфиденциальности",
    tagline: "FIDEM серьёзно относится к вашим данным",
    sections: [
      ["Какие данные собираются", [
        "Данные профиля: имя, возраст, пол, регион, образование, профессия, био и параметры поиска; фото профиля; идентификатор Telegram (при входе через Telegram); активность в приложении: просмотры, лайки, сообщения, история платежей; добровольное подтверждение локации (только с вашего разрешения; точные координаты никогда не показываются другим пользователям).",
      ]],
      ["Цели использования", [
        "Данные используются только для оказания сервиса: подбор совместимых кандидатов, обеспечение безопасности, обработка платежей и поддержка. Ваши данные НЕ ПРОДАЮТСЯ третьим лицам.",
      ]],
      ["Платёжные данные", [
        "Платежи проводятся через систему CLICK. Номер карты и другие платёжные реквизиты НЕ хранятся на серверах FIDEM — они обрабатываются только на стороне CLICK. Номер карты для вывода используется только для перевода средств.",
      ]],
      ["Сторонние сервисы", [
        "CLICK — обработка платежей; Telegram — аутентификация и уведомления; AI-проверка фото — подтверждение, что на фото реальное человеческое лицо (фото отправляется только для проверки и не используется для обучения); техническая аналитика и мониторинг ошибок (содержимое личной переписки не передаётся).",
      ]],
      ["Защита фото и профиля", [
        "Закрытые фото показываются только пользователям, которым вы дали разрешение, и не передаются без него. Сохранение и шаринг фото внутри приложения ограничены. При включённом скрытом режиме ваш профиль не отображается в поиске и списках.",
      ]],
      ["Срок хранения и удаление", [
        "Данные хранятся, пока аккаунт активен. Для удаления аккаунта и связанных данных обратитесь в поддержку: t.me/FidemAppSupport",
      ]],
      ["Согласие", [
        "Ставя галочку согласия при регистрации, вы соглашаетесь на обработку данных в соответствии с настоящей политикой. Политика может обновляться; о существенных изменениях вы будете уведомлены.",
      ]],
    ],
  },
  en: {
    title: "Privacy Policy",
    tagline: "FIDEM takes your data seriously",
    sections: [
      ["What data we collect", [
        "Profile data: name, age, gender, region, education, profession, bio and search preferences; profile photo; Telegram identifier (when signing in via Telegram); in-app activity: views, likes, messages, payment history; optional location verification (only with your permission; exact coordinates are never shown to other users).",
      ]],
      ["How data is used", [
        "Data is used solely to provide the service: matching compatible candidates, safety, payment processing and support. Your data is NOT SOLD to third parties.",
      ]],
      ["Payment data", [
        "Payments are processed via CLICK. Your card number and other payment details are NOT stored on FIDEM servers — they are processed on CLICK's side only. A card number entered for withdrawal is used solely to transfer funds.",
      ]],
      ["Third-party services", [
        "CLICK — payment processing; Telegram — authentication and notifications; AI photo verification — confirming a profile photo shows a real human face (sent for verification only, never used for training); technical analytics and error monitoring (private message contents are never transmitted).",
      ]],
      ["Photo and profile protection", [
        "Locked photos are shown only to users you approve and are never served without permission. Saving and sharing photos inside the app is restricted. With hidden mode on, your profile does not appear in search or lists.",
      ]],
      ["Retention and deletion", [
        "Data is kept while the account is active. To delete your account and related data, contact support: t.me/FidemAppSupport",
      ]],
      ["Consent", [
        "By ticking the consent checkbox at signup you agree to your data being processed under this policy. The policy may be updated; you will be notified of material changes.",
      ]],
    ],
  },
};

export default function Privacy() {
  const { lang } = useApp();
  const c = P[lang] || P.uz;
  return (
    <div className="min-h-[100dvh] bg-background">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <button type="button" onClick={() => window.history.back()} className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="privacy-back">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-heading font-semibold text-lg flex items-center gap-2"><ShieldCheck className="w-4 h-4" /> {c.title}</span>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-6 space-y-6 pb-16" data-testid="privacy-page">
        <p className="text-xs text-muted-foreground">v1.0 · {c.tagline}</p>
        {c.sections.map(([title, paras], i) => (
          <section key={i} className="space-y-2">
            <h2 className="font-heading text-base font-semibold">{i + 1}. {title}</h2>
            <div className="text-sm text-muted-foreground leading-relaxed space-y-2">
              {paras.map((p, j) => <p key={j}>{p}</p>)}
            </div>
          </section>
        ))}
        <p className="text-sm">
          <a className="text-primary underline" href="https://t.me/FidemAppSupport" target="_blank" rel="noreferrer">t.me/FidemAppSupport</a>
        </p>
      </main>
    </div>
  );
}

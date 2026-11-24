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
        "Profil ma'lumotlari: ism, yosh, jins, hudud, ma'lumoti, kasbi, bio va qidiruv afzalliklari; profil rasmi; Telegram identifikatori (Telegram orqali kirilganda) yoki email va parol (parol faqat qaytarib bo'lmaydigan shifrlangan ko'rinishda saqlanadi); ilova ichidagi faoliyat: ko'rishlar, yoqtirishlar, xabarlar, to'lovlar tarixi; ixtiyoriy joylashuv tasdig'i (faqat siz ruxsat bersangiz; aniq koordinatalar boshqa foydalanuvchilarga hech qachon ko'rsatilmaydi).",
      ]],
      ["Foydalanish maqsadi", [
        "Ma'lumotlar faqat xizmatni ko'rsatish uchun ishlatiladi: mos nomzodlarni tanlash, xavfsizlikni ta'minlash, to'lovlarni qayta ishlash va qo'llab-quvvatlash. Ma'lumotlaringiz uchinchi shaxslarga SOTILMAYDI.",
      ]],
      ["To'lov ma'lumotlari", [
        "To'lovlar bank kartasiga o'tkazma orqali amalga oshiriladi va to'lov hamkori tomonidan tasdiqlanadi. O'tkazma uchun ishlatilgan kartangiz rekvizitlari FIDEM serverlarida saqlanmaydi. Pul yechish uchun kiritgan karta raqamingiz va egasining ismi so'rovni bajarish uchun saqlanadi; hisob o'chirilsa, kartadan faqat oxirgi 4 raqam qoladi. Balans to'ldirishda yuborgan chek rasmingiz hisob o'chirilganda o'chiriladi.",
      ]],
      ["Uchinchi tomon xizmatlari", [
        "To'lov hamkori — o'tkazmalarni tasdiqlash; Telegram — autentifikatsiya va bildirishnomalar; Google (Gemini API) — sun'iy intellekt xizmatlari: profil va selfie rasmlarini tekshirish, rasmlar bir odamga tegishliligini solishtirish, chat xabarlarini qoidabuzarlikka tekshirish (moderatsiya), FIDEM yordamchisi bilan suhbat va moslik tahlili. Bu ma'lumotlar faqat shu maqsadlarda yuboriladi; FIDEM ularni sun'iy intellekt modellarini o'qitish uchun ishlatmaydi. Texnik analitika va xatolik kuzatuvi (shaxsiy yozishmalar mazmuni yuborilmaydi).",
      ]],
      ["Rasm va profil himoyasi", [
        "Yopiq rasmlar faqat siz ruxsat bergan foydalanuvchilarga ko'rsatiladi va serverdan ruxsatsiz uzatilmaydi. Ilova ichida rasmlarni saqlab olish va ulashish funksiyalari cheklangan. Maxfiy rejim yoqilganda profilingiz qidiruv va ro'yxatlarda ko'rinmaydi.",
      ]],
      ["Saqlash muddati va o'chirish", [
        "Ma'lumotlar akkaunt faol bo'lgan davrda saqlanadi. Akkauntni o'zingiz o'chirishingiz mumkin: Men → Sozlamalar → «Hisobni o'chirish» (yoki ilovaning /delete-account sahifasi). O'chirilganda profil, rasmlar, selfie, suhbatlar, yoqtirishlar, bloklar, bildirishnomalar va joylashuv o'chiriladi. Hisob-kitob va xavfsizlik uchun shaxsiy ma'lumotsiz saqlanadi: to'lovlar hisobi, shikoyat yozuvlari (matnsiz) va taqiqlangan hisoblar uchun shifrlangan belgi. Kira olmasangiz, qo'llab-quvvatlashga murojaat qiling: t.me/Medik005",
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
        "Данные профиля: имя, возраст, пол, регион, образование, профессия, био и параметры поиска; фото профиля; идентификатор Telegram (при входе через Telegram) или email и пароль (пароль хранится только в необратимо зашифрованном виде); активность в приложении: просмотры, лайки, сообщения, история платежей; добровольное подтверждение локации (только с вашего разрешения; точные координаты никогда не показываются другим пользователям).",
      ]],
      ["Цели использования", [
        "Данные используются только для оказания сервиса: подбор совместимых кандидатов, обеспечение безопасности, обработка платежей и поддержка. Ваши данные НЕ ПРОДАЮТСЯ третьим лицам.",
      ]],
      ["Платёжные данные", [
        "Платежи проводятся переводом на банковскую карту и подтверждаются платёжным партнёром. Реквизиты вашей карты, с которой вы переводите, на серверах FIDEM не хранятся. Номер карты и имя владельца, указанные для вывода, хранятся для выполнения заявки; при удалении аккаунта остаются только последние 4 цифры карты. Фото чека, отправленное при пополнении баланса, удаляется вместе с аккаунтом.",
      ]],
      ["Сторонние сервисы", [
        "Платёжный партнёр — подтверждение переводов; Telegram — аутентификация и уведомления; Google (Gemini API) — сервисы ИИ: проверка фото профиля и селфи, сравнение, что фото принадлежат одному человеку, проверка сообщений чата на нарушения (модерация), диалог с помощником FIDEM и анализ совместимости. Эти данные отправляются только для перечисленных целей; FIDEM не использует их для обучения моделей ИИ. Техническая аналитика и мониторинг ошибок (содержимое личной переписки не передаётся).",
      ]],
      ["Защита фото и профиля", [
        "Закрытые фото показываются только пользователям, которым вы дали разрешение, и не передаются без него. Сохранение и шаринг фото внутри приложения ограничены. При включённом скрытом режиме ваш профиль не отображается в поиске и списках.",
      ]],
      ["Срок хранения и удаление", [
        "Данные хранятся, пока аккаунт активен. Вы можете удалить аккаунт сами: Профиль → Настройки → «Удалить аккаунт» (или страница /delete-account в приложении). При удалении стираются анкета, фото, селфи, переписки, лайки, блокировки, уведомления и геолокация. Для учёта и безопасности без личных данных остаются: учёт платежей, записи жалоб (без текста) и хеш-метка заблокированных аккаунтов. Если не можете войти, обратитесь в поддержку: t.me/Medik005",
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
        "Profile data: name, age, gender, region, education, profession, bio and search preferences; profile photo; Telegram identifier (when signing in via Telegram) or email and password (the password is stored only in irreversibly encrypted form); in-app activity: views, likes, messages, payment history; optional location verification (only with your permission; exact coordinates are never shown to other users).",
      ]],
      ["How data is used", [
        "Data is used solely to provide the service: matching compatible candidates, safety, payment processing and support. Your data is NOT SOLD to third parties.",
      ]],
      ["Payment data", [
        "Payments are made by transfer to a bank card and confirmed by our payment partner. The details of the card you pay from are not stored on FIDEM servers. A card number and holder name you enter for a withdrawal are kept to carry out the request; if you delete your account, only the last 4 digits of the card remain. A receipt photo you sent when topping up your balance is deleted with your account.",
      ]],
      ["Third-party services", [
        "Payment partner — confirming transfers; Telegram — authentication and notifications; Google (Gemini API) — AI services: checking profile and selfie photos, comparing that photos show one person, checking chat messages for rule violations (moderation), conversations with the FIDEM assistant, and compatibility analysis. This data is sent only for those purposes; FIDEM does not use it to train AI models. Technical analytics and error monitoring (private message contents are never transmitted).",
      ]],
      ["Photo and profile protection", [
        "Locked photos are shown only to users you approve and are never served without permission. Saving and sharing photos inside the app is restricted. With hidden mode on, your profile does not appear in search or lists.",
      ]],
      ["Retention and deletion", [
        "Data is kept while the account is active. You can delete your account yourself: Me → Settings → \"Delete account\" (or the app's /delete-account page). Deleting erases your profile, photos, selfie, chats, likes, blocks, notifications and location. For accounting and safety, these remain without personal data: payment accounting, report records (without their text) and a hashed marker for banned accounts. If you can't sign in, contact support: t.me/Medik005",
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
          <a className="text-primary underline" href="https://t.me/Medik005" target="_blank" rel="noreferrer">t.me/Medik005</a>
        </p>
      </main>
    </div>
  );
}

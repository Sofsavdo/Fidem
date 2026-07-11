import React from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, FileText } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

// Legal document, localized uz/ru/en. The Uzbek text is the canonical
// version users consent to; version bumps must also bump terms_version in
// backend/routers/auth_r.py so re-consent can be required.
export const TERMS_VERSION = "1.0";

const T = {
  uz: {
    title: "Foydalanish shartlari",
    tagline: "FIDEM — jiddiy tanishuv va oila qurish platformasi",
    privacyLink: "Maxfiylik siyosati",
    sections: [
      ["Umumiy qoidalar", [
        "FIDEM — jiddiy niyatdagi insonlar uchun tanishuv platformasi. Ilovadan faqat 18 yoshga to'lgan shaxslar foydalanishi mumkin.",
        "Ro'yxatdan o'tishda rozilik belgilarini (galochka) qo'yish — ushbu shartlarni o'qib chiqqaningiz, tushunganingiz va ularga TO'LIQ ROZILIK bildirganingizni tasdiqlovchi elektron imzo hisoblanadi. Rozilik sanasi va shartlar versiyasi tizimda saqlanadi.",
      ]],
      ["Profil va haqqoniylik", [
        "Foydalanuvchi o'zi haqida haqqoniy ma'lumot kiritish, o'z rasmini joylash va bir kishiga bitta profil qoidasiga rioya qilish majburiyatini oladi. Profil rasmlari tekshiruvdan o'tadi; soxta, boshqa shaxsga tegishli yoki qoidalarga zid rasmlar rad etiladi.",
      ]],
      ["To'lovlar va tariflar", [
        "Tarif to'lovlari IXTIYORIY tanlanadi va qo'shimcha imkoniyatlar beradi. Barcha to'lovlar CLICK to'lov tizimi orqali avtomatik amalga oshiriladi.",
        "TARIF AKTIVATSIYA QILINGANDAN SO'NG TO'LANGAN PUL QAYTARILMAYDI. Tarif 30 kun amal qiladi va muddati tugagach avtomatik to'xtaydi.",
        "Ilova ichidagi balans faqat ilova ichidagi xizmatlar uchun ishlatiladi va naqd pulga yechib olinmaydi. Yechib olish faqat referal daromadiga tegishli (4-band).",
      ]],
      ["Referal dasturi va to'lovlar tartibi", [
        "Referal daromadi — platforma rivojiga qo'shgan hissangiz uchun BONUS tariqasida ixtiyoriy ajratiladigan mablag'. U kafolatlangan ish haqi yoki majburiy to'lov emas.",
        "To'lab berish tartibi: faqat administrator TASDIQLAGAN qismgina to'lab beriladi; daromad avval «hold» (kutish) holatida turadi va shu muddat tugagandan so'ng yechishga ochiladi; yechib olish so'rovi yuborilgan kundan boshlab 5 (besh) bank ish kuni ichida to'lab beriladi; administrator qoidabuzarlik yoki firibgarlikdan shubhalansa, so'rovni RAD ETISH, bekor qilish va shubhali yo'l bilan yig'ilgan balansni ANNULATSIYA QILISH (kuydirish) huquqiga ega.",
      ]],
      ["Odob-axloq, diniy va siyosiy neytrallik", [
        "Platformada o'zaro hurmat majburiy. Haqorat, kamsitish, behayo kontent taqiqlanadi.",
        "FIDEM diniy va siyosiy masalalarda NEYTRAL platforma. Davlatga yoki siyosiy vaziyatlarga qarshi fikrlar tarqatish, diniy yoki siyosiy targ'ibot olib borish taqiqlanadi. Bunday holatlarda foydalanuvchi ogohlantirishsiz BLOKLANADI.",
      ]],
      ["Muloqot xavfsizligi — foydalanuvchining o'z javobgarligi", [
        "Chatdagi muloqot xavfsizligi har bir foydalanuvchining O'Z ZIMMASIDA. Ilova foydalanuvchilar o'rtasidagi yozishmalar oqibatlariga javob bermaydi.",
        "Qat'iyan tavsiya etiladi: suhbatdoshga shaxsni tasdiqlovchi hujjat, pasport, plastik karta ma'lumotlari va ochiq (intim) rasmlarni YUBORMASLIK. Pul so'rash, tovlamachilik, shantaj va boshqa firibgarlik holatlariga uchraganda — bu uchun jabrlanuvchining o'zi javobgar bo'lib, ilova yetkazilgan zararni QOPLAB BERMAYDI. Bunday holatlarda ilovadagi SHIKOYAT QILISH va BLOKLASH funksiyalaridan darhol foydalanish kerak.",
        "Platforma o'z navbatida bunday noinsof foydalanuvchilarga qarshi kurashadi — ularni bloklash va ilovadan chiqarib yuborishga harakat qiladi, lekin jabrlanganlarning zararini qoplash majburiyatini olmaydi.",
      ]],
      ["Javobgarlik cheklovi", [
        "Xizmat «boricha» (as is) taqdim etiladi. Platforma tanishuvlar natijasini, turmush qurishni yoki muayyan foydalanuvchi bilan muloqotni kafolatlamaydi va foydalanuvchilar o'rtasidagi shaxsiy kelishmovchiliklarga aralashmaydi.",
      ]],
      ["Bloklash", [
        "Qoidalar buzilganda platforma profilni ogohlantirishsiz cheklash, bloklash yoki o'chirish huquqiga ega. Bloklangan foydalanuvchining to'lovlari qaytarilmaydi.",
      ]],
      ["O'zgartirishlar va aloqa", [
        "Shartlar yangilanishi mumkin; muhim o'zgarishlarda qayta rozilik so'raladi. Savollar uchun: t.me/FidemAppSupport",
      ]],
    ],
  },
  ru: {
    title: "Условия использования",
    tagline: "FIDEM — платформа серьёзных знакомств и создания семьи",
    privacyLink: "Политика конфиденциальности",
    sections: [
      ["Общие положения", [
        "FIDEM — платформа знакомств для людей с серьёзными намерениями. Пользоваться приложением могут только лица, достигшие 18 лет.",
        "Установка галочек согласия при регистрации является электронной подписью, подтверждающей, что вы прочитали, поняли и ПОЛНОСТЬЮ СОГЛАСНЫ с настоящими условиями. Дата согласия и версия условий сохраняются в системе.",
      ]],
      ["Профиль и достоверность", [
        "Пользователь обязуется указывать достоверные сведения о себе, размещать собственные фотографии и соблюдать правило «один человек — один профиль». Фотографии проходят проверку; поддельные, чужие или нарушающие правила фото отклоняются.",
      ]],
      ["Платежи и тарифы", [
        "Тарифы выбираются ДОБРОВОЛЬНО и дают дополнительные возможности. Все платежи проводятся автоматически через платёжную систему CLICK.",
        "ПОСЛЕ АКТИВАЦИИ ТАРИФА ОПЛАТА НЕ ВОЗВРАЩАЕТСЯ. Тариф действует 30 дней и автоматически прекращается по истечении срока.",
        "Внутренний баланс используется только для услуг внутри приложения и не обналичивается. Вывод средств касается только реферального дохода (раздел 4).",
      ]],
      ["Реферальная программа и порядок выплат", [
        "Реферальный доход — средства, добровольно выделяемые в виде БОНУСА за вклад в развитие платформы. Это не гарантированная зарплата и не обязательная выплата.",
        "Порядок выплат: выплачивается только часть, ПОДТВЕРЖДЁННАЯ администратором; доход сначала находится в статусе «hold» (ожидание) и открывается к выводу после его окончания; выплата производится в течение 5 (пяти) банковских рабочих дней со дня подачи запроса; при подозрении на нарушение или мошенничество администратор вправе ОТКЛОНИТЬ запрос, отменить его и АННУЛИРОВАТЬ подозрительно накопленный баланс.",
      ]],
      ["Этика, религиозный и политический нейтралитет", [
        "Взаимное уважение обязательно. Оскорбления, унижения и непристойный контент запрещены.",
        "FIDEM — НЕЙТРАЛЬНАЯ платформа в религиозных и политических вопросах. Распространение высказываний против государства или политической ситуации, религиозная или политическая агитация запрещены. В таких случаях пользователь БЛОКИРУЕТСЯ без предупреждения.",
      ]],
      ["Безопасность общения — ответственность пользователя", [
        "Безопасность общения в чате — ЛИЧНАЯ ОТВЕТСТВЕННОСТЬ каждого пользователя. Приложение не отвечает за последствия переписки между пользователями.",
        "Настоятельно рекомендуется: НЕ ОТПРАВЛЯТЬ собеседнику документы, паспорт, данные банковских карт и откровенные (интимные) фото. При вымогательстве, шантаже и иных видах мошенничества ответственность несёт сам пострадавший — приложение НЕ ВОЗМЕЩАЕТ ущерб. В таких случаях немедленно используйте функции ЖАЛОБЫ и БЛОКИРОВКИ.",
        "Платформа со своей стороны борется с недобросовестными пользователями — блокирует и удаляет их, но не принимает обязательств по возмещению ущерба пострадавшим.",
      ]],
      ["Ограничение ответственности", [
        "Сервис предоставляется «как есть» (as is). Платформа не гарантирует результат знакомств, вступление в брак или общение с конкретным пользователем и не вмешивается в личные разногласия между пользователями.",
      ]],
      ["Блокировка", [
        "При нарушении правил платформа вправе ограничить, заблокировать или удалить профиль без предупреждения. Платежи заблокированного пользователя не возвращаются.",
      ]],
      ["Изменения и контакты", [
        "Условия могут обновляться; при существенных изменениях запрашивается повторное согласие. Вопросы: t.me/FidemAppSupport",
      ]],
    ],
  },
  en: {
    title: "Terms of Use",
    tagline: "FIDEM — a serious dating and family-building platform",
    privacyLink: "Privacy Policy",
    sections: [
      ["General", [
        "FIDEM is a dating platform for people with serious intentions. Only persons aged 18+ may use the app.",
        "Ticking the consent checkboxes at signup is an electronic signature confirming that you have read, understood and FULLY AGREE to these terms. The consent date and terms version are stored.",
      ]],
      ["Profile and truthfulness", [
        "The user undertakes to provide truthful information, upload their own photos, and follow the one-person-one-profile rule. Profile photos are verified; fake, third-party or rule-breaking photos are rejected.",
      ]],
      ["Payments and plans", [
        "Plans are VOLUNTARY and unlock additional features. All payments are processed automatically via the CLICK payment system.",
        "PAYMENTS ARE NON-REFUNDABLE ONCE A PLAN IS ACTIVATED. A plan is valid for 30 days and ends automatically.",
        "The in-app balance is used only for in-app services and cannot be cashed out. Withdrawal applies only to referral earnings (section 4).",
      ]],
      ["Referral program and payouts", [
        "Referral earnings are funds allocated voluntarily as a BONUS for contributing to the platform's growth — not a guaranteed salary or mandatory payment.",
        "Payout rules: only the amount APPROVED by the administrator is paid; earnings first sit in 'hold' and open for withdrawal after it ends; payouts are made within 5 (five) bank business days of the request; on suspicion of abuse or fraud the administrator may REJECT the request, cancel it and ANNUL a suspiciously accumulated balance.",
      ]],
      ["Conduct, religious and political neutrality", [
        "Mutual respect is mandatory. Insults, harassment and obscene content are prohibited.",
        "FIDEM is NEUTRAL on religious and political matters. Spreading statements against the state or political situations, religious or political agitation is prohibited. Violators are BLOCKED without warning.",
      ]],
      ["Chat safety — the user's own responsibility", [
        "Chat safety is each user's OWN RESPONSIBILITY. The app is not liable for the consequences of correspondence between users.",
        "Strongly advised: NEVER send ID documents, passports, bank card details or explicit (intimate) photos. In cases of money requests, extortion, blackmail or other fraud, the victim bears the responsibility — the app does NOT compensate damages. Use the in-app REPORT and BLOCK features immediately.",
        "The platform fights bad actors — blocking and removing them — but assumes no obligation to compensate victims.",
      ]],
      ["Limitation of liability", [
        "The service is provided 'as is'. The platform does not guarantee dating outcomes, marriage, or communication with any particular user, and does not intervene in personal disputes between users.",
      ]],
      ["Blocking", [
        "On rule violations the platform may restrict, block or delete a profile without warning. A blocked user's payments are not refunded.",
      ]],
      ["Changes and contact", [
        "These terms may be updated; material changes require renewed consent. Questions: t.me/FidemAppSupport",
      ]],
    ],
  },
};

export default function Terms() {
  const { lang } = useApp();
  const c = T[lang] || T.uz;
  return (
    <div className="min-h-[100dvh] bg-background">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <button type="button" onClick={() => window.history.back()} className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="terms-back">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-heading font-semibold text-lg flex items-center gap-2"><FileText className="w-4 h-4" /> {c.title}</span>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-6 space-y-6 pb-16" data-testid="terms-page">
        <p className="text-xs text-muted-foreground">
          v{TERMS_VERSION} · {c.tagline} ·{" "}
          <Link to="/privacy" className="text-primary underline">{c.privacyLink}</Link>
        </p>
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

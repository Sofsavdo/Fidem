// Conversation question deck (the 💡 button in chat) and first-message
// openers. Plain, respectful questions for a marriage-minded chat.
export const QUESTION_DECK = {
  uz: {
    "👨‍👩‍👧 Oila": [
      "Siz uchun ideal oila qanday bo'ladi?",
      "Oilangizda eng yaxshi ko'rgan an'anangiz qaysi?",
      "Ota-onangizdan qaysi xislatni o'zingizga olgansiz?",
      "Bayramlarni qanday o'tkazishni yaxshi ko'rasiz?",
      "Farzandlar tarbiyasida nima eng muhim deb o'ylaysiz?",
    ],
    "🤲 Qadriyatlar": [
      "Hayotda eng qadrlaydigan narsangiz nima?",
      "Insonda qaysi xislatni ko'rsangiz, unga ishonasiz?",
      "Sizningcha, baxtli nikohning siri nimada?",
      "Qiyin paytda sizni nima qo'llab-quvvatlaydi?",
      "Kechirish siz uchun oson ishmi?",
    ],
    "✨ Qiziqishlar": [
      "Bo'sh vaqtingizda nima qilishni yaxshi ko'rasiz?",
      "Oxirgi o'qigan kitobingiz yoki ko'rgan filmingiz qaysi?",
      "Qaysi taomni eng zo'r pishirasiz?",
      "Qaysi shaharga borishni orzu qilasiz?",
      "Bolaligingizdagi eng yorqin xotirangiz?",
    ],
    "🌅 Kelajak": [
      "5 yildan keyin o'zingizni qayerda ko'rasiz?",
      "Qaysi shaharda yashashni xohlaysiz?",
      "Ishingizda qanday maqsadlaringiz bor?",
      "Dam olish kunini ideal qanday o'tkazgan bo'lardingiz?",
      "Hayotdagi eng katta orzuingiz nima?",
    ],
    "😄 Yengil": [
      "Choymi yoki qahva? ☕",
      "Tog'mi yoki dengiz? 🏔🌊",
      "Ertalabki odammisiz yoki kechki? 🌞🌙",
      "Sizni nima doim kuldiradi?",
      "Qaysi hayvonni eng yaxshi ko'rasiz?",
    ],
  },
  ru: {
    "👨‍👩‍👧 Семья": [
      "Какой вы представляете идеальную семью?",
      "Какая семейная традиция вам дороже всего?",
      "Какое качество вы переняли от родителей?",
      "Как вы любите отмечать праздники?",
      "Что главное в воспитании детей?",
    ],
    "🤲 Ценности": [
      "Что вы цените в жизни больше всего?",
      "Какое качество в человеке вызывает у вас доверие?",
      "В чём, по-вашему, секрет счастливого брака?",
      "Что поддерживает вас в трудную минуту?",
      "Легко ли вам прощать?",
    ],
    "✨ Интересы": [
      "Чем любите заниматься в свободное время?",
      "Какую книгу или фильм вы недавно посмотрели?",
      "Какое блюдо вы готовите лучше всего?",
      "В какой город мечтаете поехать?",
      "Самое яркое воспоминание из детства?",
    ],
    "🌅 Будущее": [
      "Где вы видите себя через 5 лет?",
      "В каком городе хотели бы жить?",
      "Какие у вас цели в работе?",
      "Как выглядел бы ваш идеальный выходной?",
      "Какая ваша самая большая мечта?",
    ],
    "😄 Легко": [
      "Чай или кофе? ☕",
      "Горы или море? 🏔🌊",
      "Жаворонок или сова? 🌞🌙",
      "Что вас всегда смешит?",
      "Какое животное вы любите больше всего?",
    ],
  },
  en: {
    "👨‍👩‍👧 Family": [
      "What does an ideal family look like to you?",
      "Which family tradition do you love most?",
      "What did you take from your parents?",
      "How do you like to spend holidays?",
      "What matters most in raising children?",
    ],
    "🤲 Values": [
      "What do you value most in life?",
      "What makes you trust someone?",
      "What's the secret of a happy marriage, to you?",
      "What keeps you going in hard times?",
      "Is forgiving easy for you?",
    ],
    "✨ Interests": [
      "What do you love doing in your free time?",
      "The last book or film you enjoyed?",
      "Which dish do you cook best?",
      "Which city do you dream of visiting?",
      "Your brightest childhood memory?",
    ],
    "🌅 Future": [
      "Where do you see yourself in 5 years?",
      "Which city would you like to live in?",
      "What are your goals at work?",
      "What would your perfect day off look like?",
      "What's your biggest dream?",
    ],
    "😄 Light": [
      "Tea or coffee? ☕",
      "Mountains or the sea? 🏔🌊",
      "Morning person or night owl? 🌞🌙",
      "What always makes you laugh?",
      "Your favourite animal?",
    ],
  },
};

// First-message openers built from the other person's profile.
export function openersFor(other, me, lang = "uz") {
  const name = (other?.name || "").split(" ")[0];
  const ALL = {
    uz: {
      region: (r) => `Assalomu alaykum, ${name}! Men ham ${r}danman 😊 Qaysi tumandansiz?`,
      job: (p) => `Assalomu alaykum, ${name}! ${p} bo'lib ishlash qanday — ishingizni yaxshi ko'rasizmi?`,
      bio: () => `Assalomu alaykum, ${name}! Profilingizdagi so'zlaringiz menga yoqdi. O'zingiz haqingizda yana nimalarni aytib berasiz?`,
      general: () => `Assalomu alaykum, ${name}! Tanishganimdan xursandman. Bo'sh vaqtingizda nima qilishni yaxshi ko'rasiz?`,
      family: () => `Assalomu alaykum! Siz uchun ideal oila qanday bo'lishi kerak deb o'ylaysiz?`,
    },
    ru: {
      region: (r) => `Здравствуйте, ${name}! Я тоже из ${r} 😊 Из какого вы района?`,
      job: (p) => `Здравствуйте, ${name}! Как вам работа (${p}) — нравится?`,
      bio: () => `Здравствуйте, ${name}! Мне понравилось, что вы написали о себе. Расскажете ещё?`,
      general: () => `Здравствуйте, ${name}! Рад(а) знакомству. Чем любите заниматься в свободное время?`,
      family: () => `Здравствуйте! Какой вы представляете идеальную семью?`,
    },
    en: {
      region: (r) => `Hi ${name}! I'm from ${r} too 😊 Which district are you from?`,
      job: (p) => `Hi ${name}! How do you like working as ${p}?`,
      bio: () => `Hi ${name}! I liked what you wrote about yourself. Tell me more?`,
      general: () => `Hi ${name}! Nice to meet you. What do you love doing in your free time?`,
      family: () => `Hi! What does an ideal family look like to you?`,
    },
  };
  const T = ALL[lang] || ALL.uz;
  const out = [];
  if (other?.region && me?.region && other.region === me.region) out.push(T.region(other.region));
  if (other?.profession) out.push(T.job(other.profession));
  if ((other?.bio || "").length > 20) out.push(T.bio());
  out.push(T.general(), T.family());
  return out.slice(0, 3);
}

export const ASSISTANT_CHIPS = {
  uz: ["Premium qancha turadi?", "Selfie tasdiq qanday o'tiladi?", "Kontakt qanday almashiladi?", "Birinchi xabarga maslahat bering"],
  ru: ["Сколько стоит Premium?", "Как пройти селфи-проверку?", "Как обменяться контактами?", "Подскажите первое сообщение"],
  en: ["How much is Premium?", "How does the selfie check work?", "How do I exchange contacts?", "Help me with a first message"],
};

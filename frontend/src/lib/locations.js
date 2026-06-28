// FIDEM — global countries + regions database.
// Used by Onboarding, Settings filters, Candidates filter.
// Format: { code: ISO-2, name, flag, regions: [..] | null (=> free text) }
//
// Regions are provided for CIS region + select large markets.
// For countries without a regions array, the form renders a free-text input.

export const COUNTRIES = [
  // --- CIS / Central Asia (priority markets) ---
  {
    code: "UZ",
    name: "Uzbekistan",
    name_ru: "Узбекистан",
    name_uz: "O'zbekiston",
    flag: "🇺🇿",
    regions: [
      "Toshkent shahri", "Toshkent viloyati", "Samarqand", "Buxoro", "Andijon",
      "Farg'ona", "Namangan", "Qashqadaryo", "Surxondaryo", "Sirdaryo",
      "Jizzax", "Navoiy", "Xorazm", "Qoraqalpog'iston",
    ],
  },
  {
    code: "KZ",
    name: "Kazakhstan",
    name_ru: "Казахстан",
    name_uz: "Qozog'iston",
    flag: "🇰🇿",
    regions: [
      "Almaty", "Astana (Nur-Sultan)", "Shymkent", "Aktobe", "Karaganda",
      "Taraz", "Pavlodar", "Ust-Kamenogorsk", "Semey", "Atyrau", "Kostanay",
      "Kyzylorda", "Uralsk", "Petropavl", "Aktau", "Temirtau", "Turkistan",
    ],
  },
  {
    code: "KG",
    name: "Kyrgyzstan",
    name_ru: "Кыргызстан",
    name_uz: "Qirg'iziston",
    flag: "🇰🇬",
    regions: [
      "Bishkek", "Osh", "Jalal-Abad", "Karakol", "Tokmok", "Kara-Balta",
      "Naryn", "Talas", "Batken", "Cholpon-Ata", "Uzgen", "Kyzyl-Kiya",
    ],
  },
  {
    code: "TJ",
    name: "Tajikistan",
    name_ru: "Таджикистан",
    name_uz: "Tojikiston",
    flag: "🇹🇯",
    regions: [
      "Dushanbe", "Khujand", "Bokhtar", "Kulob", "Istaravshan",
      "Tursunzoda", "Khorugh", "Konibodom", "Vahdat", "Panjakent",
    ],
  },
  {
    code: "TM",
    name: "Turkmenistan",
    name_ru: "Туркменистан",
    name_uz: "Turkmaniston",
    flag: "🇹🇲",
    regions: ["Ashgabat", "Türkmenabat", "Daşoguz", "Mary", "Balkanabat", "Bayramaly", "Tejen", "Türkmenbaşy"],
  },
  {
    code: "AZ",
    name: "Azerbaijan",
    name_ru: "Азербайджан",
    name_uz: "Ozarbayjon",
    flag: "🇦🇿",
    regions: ["Baku", "Ganja", "Sumqayit", "Mingachevir", "Lankaran", "Shirvan", "Nakhchivan", "Sheki", "Yevlakh"],
  },
  {
    code: "RU",
    name: "Russia",
    name_ru: "Россия",
    name_uz: "Rossiya",
    flag: "🇷🇺",
    regions: [
      "Moscow", "Saint Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan",
      "Nizhny Novgorod", "Chelyabinsk", "Samara", "Omsk", "Rostov-on-Don",
      "Ufa", "Krasnoyarsk", "Voronezh", "Perm", "Volgograd", "Krasnodar",
      "Saratov", "Tyumen", "Tolyatti", "Izhevsk", "Barnaul", "Ulyanovsk",
      "Irkutsk", "Khabarovsk", "Vladivostok", "Yaroslavl", "Makhachkala",
      "Tomsk", "Orenburg", "Kemerovo", "Novokuznetsk", "Ryazan", "Astrakhan",
      "Penza", "Lipetsk", "Tula", "Kirov", "Cheboksary", "Kaliningrad",
    ],
  },
  {
    code: "UA",
    name: "Ukraine",
    name_ru: "Украина",
    name_uz: "Ukraina",
    flag: "🇺🇦",
    regions: ["Kyiv", "Kharkiv", "Odesa", "Dnipro", "Lviv", "Zaporizhzhia", "Vinnytsia", "Poltava", "Chernihiv", "Cherkasy"],
  },
  {
    code: "BY",
    name: "Belarus",
    name_ru: "Беларусь",
    name_uz: "Belarus",
    flag: "🇧🇾",
    regions: ["Minsk", "Gomel", "Mogilev", "Vitebsk", "Grodno", "Brest"],
  },
  {
    code: "GE",
    name: "Georgia",
    name_ru: "Грузия",
    name_uz: "Gruziya",
    flag: "🇬🇪",
    regions: ["Tbilisi", "Batumi", "Kutaisi", "Rustavi", "Gori", "Zugdidi", "Poti", "Telavi"],
  },
  {
    code: "AM",
    name: "Armenia",
    name_ru: "Армения",
    name_uz: "Armaniston",
    flag: "🇦🇲",
    regions: ["Yerevan", "Gyumri", "Vanadzor", "Vagharshapat", "Hrazdan", "Abovyan", "Kapan"],
  },
  {
    code: "MD",
    name: "Moldova",
    name_ru: "Молдова",
    name_uz: "Moldova",
    flag: "🇲🇩",
    regions: ["Chișinău", "Tiraspol", "Bălți", "Bender", "Cahul", "Orhei", "Ungheni"],
  },

  // --- Turkey & Middle East ---
  {
    code: "TR",
    name: "Turkey",
    name_ru: "Турция",
    name_uz: "Turkiya",
    flag: "🇹🇷",
    regions: [
      "Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Gaziantep",
      "Konya", "Kayseri", "Mersin", "Eskişehir", "Diyarbakır", "Samsun",
      "Denizli", "Şanlıurfa", "Trabzon", "Malatya", "Erzurum", "Van",
    ],
  },
  { code: "AE", name: "United Arab Emirates", name_ru: "ОАЭ", name_uz: "BAA", flag: "🇦🇪", regions: ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"] },
  { code: "SA", name: "Saudi Arabia", name_ru: "Саудовская Аравия", name_uz: "Saudiya", flag: "🇸🇦", regions: ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Tabuk", "Buraidah", "Abha"] },
  { code: "QA", name: "Qatar", name_ru: "Катар", name_uz: "Qatar", flag: "🇶🇦", regions: null },
  { code: "KW", name: "Kuwait", name_ru: "Кувейт", name_uz: "Quvayt", flag: "🇰🇼", regions: null },
  { code: "OM", name: "Oman", name_ru: "Оман", name_uz: "Ummon", flag: "🇴🇲", regions: null },
  { code: "BH", name: "Bahrain", name_ru: "Бахрейн", name_uz: "Bahrayn", flag: "🇧🇭", regions: null },
  { code: "JO", name: "Jordan", name_ru: "Иордания", name_uz: "Iordaniya", flag: "🇯🇴", regions: null },
  { code: "LB", name: "Lebanon", name_ru: "Ливан", name_uz: "Livan", flag: "🇱🇧", regions: null },
  { code: "EG", name: "Egypt", name_ru: "Египет", name_uz: "Misr", flag: "🇪🇬", regions: ["Cairo", "Alexandria", "Giza", "Shubra El Kheima", "Port Said", "Suez", "Luxor", "Aswan", "Mansoura"] },
  { code: "IL", name: "Israel", name_ru: "Израиль", name_uz: "Isroil", flag: "🇮🇱", regions: ["Jerusalem", "Tel Aviv", "Haifa", "Rishon LeZion", "Petah Tikva", "Ashdod", "Netanya", "Beer Sheva"] },
  { code: "IR", name: "Iran", name_ru: "Иран", name_uz: "Eron", flag: "🇮🇷", regions: null },
  { code: "PK", name: "Pakistan", name_ru: "Пакистан", name_uz: "Pokiston", flag: "🇵🇰", regions: ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta"] },
  { code: "AF", name: "Afghanistan", name_ru: "Афганистан", name_uz: "Afg'oniston", flag: "🇦🇫", regions: null },

  // --- North America ---
  {
    code: "US",
    name: "United States",
    name_ru: "США",
    name_uz: "AQSh",
    flag: "🇺🇸",
    regions: [
      "California", "Texas", "Florida", "New York", "Pennsylvania", "Illinois",
      "Ohio", "Georgia", "North Carolina", "Michigan", "New Jersey", "Virginia",
      "Washington", "Arizona", "Massachusetts", "Tennessee", "Indiana", "Missouri",
      "Maryland", "Wisconsin", "Colorado", "Minnesota", "South Carolina", "Alabama",
      "Louisiana", "Kentucky", "Oregon", "Oklahoma", "Connecticut", "Utah",
      "Nevada", "Arkansas", "Mississippi", "Kansas", "Iowa", "New Mexico",
      "Nebraska", "Idaho", "West Virginia", "Hawaii", "Maine", "Montana",
      "Rhode Island", "Delaware", "South Dakota", "North Dakota", "Alaska",
      "Vermont", "Wyoming", "New Hampshire",
    ],
  },
  {
    code: "CA",
    name: "Canada",
    name_ru: "Канада",
    name_uz: "Kanada",
    flag: "🇨🇦",
    regions: ["Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba", "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland and Labrador", "Prince Edward Island"],
  },
  { code: "MX", name: "Mexico", name_ru: "Мексика", name_uz: "Meksika", flag: "🇲🇽", regions: null },

  // --- Europe ---
  { code: "GB", name: "United Kingdom", name_ru: "Великобритания", name_uz: "Buyuk Britaniya", flag: "🇬🇧", regions: ["England", "Scotland", "Wales", "Northern Ireland", "London", "Manchester", "Birmingham", "Liverpool", "Glasgow", "Edinburgh"] },
  {
    code: "DE",
    name: "Germany",
    name_ru: "Германия",
    name_uz: "Germaniya",
    flag: "🇩🇪",
    regions: ["Berlin", "Hamburg", "Bavaria", "Baden-Württemberg", "North Rhine-Westphalia", "Hesse", "Saxony", "Lower Saxony", "Rhineland-Palatinate", "Schleswig-Holstein", "Brandenburg", "Saxony-Anhalt", "Thuringia", "Mecklenburg-Vorpommern", "Bremen", "Saarland"],
  },
  { code: "FR", name: "France", name_ru: "Франция", name_uz: "Fransiya", flag: "🇫🇷", regions: ["Paris (Île-de-France)", "Provence-Alpes-Côte d'Azur", "Auvergne-Rhône-Alpes", "Nouvelle-Aquitaine", "Occitanie", "Hauts-de-France", "Grand Est", "Pays de la Loire", "Brittany", "Normandy", "Bourgogne-Franche-Comté", "Centre-Val de Loire", "Corsica"] },
  { code: "IT", name: "Italy", name_ru: "Италия", name_uz: "Italiya", flag: "🇮🇹", regions: ["Rome (Lazio)", "Milan (Lombardy)", "Naples (Campania)", "Turin (Piedmont)", "Sicily", "Veneto", "Emilia-Romagna", "Tuscany", "Apulia", "Calabria", "Sardinia"] },
  { code: "ES", name: "Spain", name_ru: "Испания", name_uz: "Ispaniya", flag: "🇪🇸", regions: ["Madrid", "Catalonia", "Andalusia", "Valencia", "Galicia", "Castile and León", "Basque Country", "Castile-La Mancha", "Canary Islands", "Aragon", "Murcia", "Extremadura", "Asturias", "Navarre", "Cantabria"] },
  { code: "NL", name: "Netherlands", name_ru: "Нидерланды", name_uz: "Niderlandiya", flag: "🇳🇱", regions: ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Groningen", "Tilburg", "Almere", "Breda", "Nijmegen"] },
  { code: "BE", name: "Belgium", name_ru: "Бельгия", name_uz: "Belgiya", flag: "🇧🇪", regions: null },
  { code: "CH", name: "Switzerland", name_ru: "Швейцария", name_uz: "Shveytsariya", flag: "🇨🇭", regions: ["Zurich", "Geneva", "Basel", "Bern", "Lausanne", "Lucerne", "Lugano", "St. Gallen"] },
  { code: "AT", name: "Austria", name_ru: "Австрия", name_uz: "Avstriya", flag: "🇦🇹", regions: null },
  { code: "SE", name: "Sweden", name_ru: "Швеция", name_uz: "Shvetsiya", flag: "🇸🇪", regions: null },
  { code: "NO", name: "Norway", name_ru: "Норвегия", name_uz: "Norvegiya", flag: "🇳🇴", regions: null },
  { code: "DK", name: "Denmark", name_ru: "Дания", name_uz: "Daniya", flag: "🇩🇰", regions: null },
  { code: "FI", name: "Finland", name_ru: "Финляндия", name_uz: "Finlandiya", flag: "🇫🇮", regions: null },
  { code: "PL", name: "Poland", name_ru: "Польша", name_uz: "Polsha", flag: "🇵🇱", regions: ["Warsaw", "Kraków", "Łódź", "Wrocław", "Poznań", "Gdańsk", "Szczecin", "Bydgoszcz", "Lublin", "Katowice"] },
  { code: "CZ", name: "Czechia", name_ru: "Чехия", name_uz: "Chexiya", flag: "🇨🇿", regions: null },
  { code: "PT", name: "Portugal", name_ru: "Португалия", name_uz: "Portugaliya", flag: "🇵🇹", regions: null },
  { code: "GR", name: "Greece", name_ru: "Греция", name_uz: "Yunoniston", flag: "🇬🇷", regions: null },
  { code: "RO", name: "Romania", name_ru: "Румыния", name_uz: "Ruminiya", flag: "🇷🇴", regions: null },
  { code: "HU", name: "Hungary", name_ru: "Венгрия", name_uz: "Vengriya", flag: "🇭🇺", regions: null },
  { code: "IE", name: "Ireland", name_ru: "Ирландия", name_uz: "Irlandiya", flag: "🇮🇪", regions: null },

  // --- Asia ---
  {
    code: "CN",
    name: "China",
    name_ru: "Китай",
    name_uz: "Xitoy",
    flag: "🇨🇳",
    regions: ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chongqing", "Tianjin", "Chengdu", "Wuhan", "Xi'an", "Hangzhou", "Nanjing", "Suzhou", "Qingdao", "Dalian", "Harbin", "Urumqi", "Kunming"],
  },
  {
    code: "IN",
    name: "India",
    name_ru: "Индия",
    name_uz: "Hindiston",
    flag: "🇮🇳",
    regions: ["Maharashtra (Mumbai)", "Delhi NCR", "Karnataka (Bangalore)", "Tamil Nadu (Chennai)", "West Bengal (Kolkata)", "Telangana (Hyderabad)", "Gujarat", "Uttar Pradesh", "Rajasthan", "Punjab", "Kerala", "Haryana", "Madhya Pradesh", "Bihar", "Odisha", "Assam"],
  },
  { code: "JP", name: "Japan", name_ru: "Япония", name_uz: "Yaponiya", flag: "🇯🇵", regions: ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo", "Fukuoka", "Kobe", "Kyoto", "Kawasaki", "Hiroshima"] },
  { code: "KR", name: "South Korea", name_ru: "Южная Корея", name_uz: "Janubiy Koreya", flag: "🇰🇷", regions: ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Ulsan", "Suwon"] },
  { code: "MY", name: "Malaysia", name_ru: "Малайзия", name_uz: "Malayziya", flag: "🇲🇾", regions: null },
  { code: "SG", name: "Singapore", name_ru: "Сингапур", name_uz: "Singapur", flag: "🇸🇬", regions: null },
  { code: "ID", name: "Indonesia", name_ru: "Индонезия", name_uz: "Indoneziya", flag: "🇮🇩", regions: null },
  { code: "TH", name: "Thailand", name_ru: "Таиланд", name_uz: "Tailand", flag: "🇹🇭", regions: null },
  { code: "VN", name: "Vietnam", name_ru: "Вьетнам", name_uz: "Vyetnam", flag: "🇻🇳", regions: null },
  { code: "PH", name: "Philippines", name_ru: "Филиппины", name_uz: "Filippin", flag: "🇵🇭", regions: null },
  { code: "BD", name: "Bangladesh", name_ru: "Бангладеш", name_uz: "Bangladesh", flag: "🇧🇩", regions: null },
  { code: "LK", name: "Sri Lanka", name_ru: "Шри-Ланка", name_uz: "Shri-Lanka", flag: "🇱🇰", regions: null },
  { code: "MM", name: "Myanmar", name_ru: "Мьянма", name_uz: "Myanma", flag: "🇲🇲", regions: null },

  // --- Oceania ---
  { code: "AU", name: "Australia", name_ru: "Австралия", name_uz: "Avstraliya", flag: "🇦🇺", regions: ["New South Wales", "Victoria", "Queensland", "Western Australia", "South Australia", "Tasmania", "Australian Capital Territory", "Northern Territory"] },
  { code: "NZ", name: "New Zealand", name_ru: "Новая Зеландия", name_uz: "Yangi Zelandiya", flag: "🇳🇿", regions: null },

  // --- Africa (top markets) ---
  { code: "ZA", name: "South Africa", name_ru: "ЮАР", name_uz: "JAR", flag: "🇿🇦", regions: null },
  { code: "NG", name: "Nigeria", name_ru: "Нигерия", name_uz: "Nigeriya", flag: "🇳🇬", regions: null },
  { code: "KE", name: "Kenya", name_ru: "Кения", name_uz: "Keniya", flag: "🇰🇪", regions: null },
  { code: "MA", name: "Morocco", name_ru: "Марокко", name_uz: "Marokash", flag: "🇲🇦", regions: null },
  { code: "DZ", name: "Algeria", name_ru: "Алжир", name_uz: "Jazoir", flag: "🇩🇿", regions: null },
  { code: "TN", name: "Tunisia", name_ru: "Тунис", name_uz: "Tunis", flag: "🇹🇳", regions: null },

  // --- Latin America (top markets) ---
  { code: "BR", name: "Brazil", name_ru: "Бразилия", name_uz: "Braziliya", flag: "🇧🇷", regions: null },
  { code: "AR", name: "Argentina", name_ru: "Аргентина", name_uz: "Argentina", flag: "🇦🇷", regions: null },
  { code: "CL", name: "Chile", name_ru: "Чили", name_uz: "Chili", flag: "🇨🇱", regions: null },
  { code: "CO", name: "Colombia", name_ru: "Колумбия", name_uz: "Kolumbiya", flag: "🇨🇴", regions: null },
  { code: "PE", name: "Peru", name_ru: "Перу", name_uz: "Peru", flag: "🇵🇪", regions: null },
];

// Helper: find country meta by name (English canonical, used in DB).
export function findCountry(name) {
  if (!name) return null;
  const lower = String(name).toLowerCase();
  return COUNTRIES.find(
    (c) =>
      c.name.toLowerCase() === lower ||
      (c.name_uz && c.name_uz.toLowerCase() === lower) ||
      (c.name_ru && c.name_ru.toLowerCase() === lower) ||
      c.code.toLowerCase() === lower,
  ) || null;
}

// Localized name lookup
export function countryLabel(country, lang = "en") {
  if (!country) return "";
  if (lang === "uz" && country.name_uz) return country.name_uz;
  if (lang === "ru" && country.name_ru) return country.name_ru;
  return country.name;
}

export function getRegionsFor(countryName) {
  const c = findCountry(countryName);
  return c?.regions || null;
}

export default COUNTRIES;

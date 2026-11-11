// Districts (tumanlar) and district-level cities of Uzbekistan, keyed by the
// region names used in lib/locations.js. Other countries have no district list,
// so the picker falls back to free text there.
const UZ_DISTRICTS = {
  "Toshkent shahri": [
    "Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug'bek", "Olmazor", "Sergeli",
    "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yangihayot", "Yashnobod", "Yunusobod",
  ],
  "Toshkent viloyati": [
    "Angren shahri", "Bekobod shahri", "Chirchiq shahri", "Nurafshon shahri", "Olmaliq shahri",
    "Ohangaron shahri", "Yangiyo'l shahri",
    "Bekobod", "Bo'ka", "Bo'stonliq", "Chinoz", "Ohangaron", "Oqqo'rg'on", "O'rtachirchiq",
    "Parkent", "Piskent", "Qibray", "Quyichirchiq", "Toshkent tumani", "Yangiyo'l",
    "Yuqorichirchiq", "Zangiota",
  ],
  "Andijon": [
    "Andijon shahri", "Xonobod shahri",
    "Andijon tumani", "Asaka", "Baliqchi", "Bo'ston", "Buloqboshi", "Izboskan", "Jalaquduq",
    "Marhamat", "Oltinko'l", "Paxtaobod", "Qo'rg'ontepa", "Shahrixon", "Ulug'nor", "Xo'jaobod",
  ],
  "Samarqand": [
    "Samarqand shahri", "Kattaqo'rg'on shahri",
    "Bulung'ur", "Ishtixon", "Jomboy", "Kattaqo'rg'on tumani", "Narpay", "Nurobod", "Oqdaryo",
    "Paxtachi", "Payariq", "Pastdarg'om", "Qo'shrabot", "Samarqand tumani", "Toyloq", "Urgut",
  ],
  "Buxoro": [
    "Buxoro shahri", "Kogon shahri",
    "Buxoro tumani", "G'ijduvon", "Jondor", "Kogon", "Olot", "Peshku", "Qorako'l",
    "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent",
  ],
  "Farg'ona": [
    "Farg'ona shahri", "Marg'ilon shahri", "Qo'qon shahri", "Quvasoy shahri",
    "Bag'dod", "Beshariq", "Buvayda", "Dang'ara", "Farg'ona tumani", "Furqat", "Oltiariq",
    "Qo'shtepa", "Quva", "Rishton", "So'x", "Toshloq", "Uchko'prik", "O'zbekiston", "Yozyovon",
  ],
  "Namangan": [
    "Namangan shahri",
    "Chortoq", "Chust", "Davlatobod", "Kosonsoy", "Mingbuloq", "Namangan tumani", "Norin",
    "Pop", "To'raqo'rg'on", "Uchqo'rg'on", "Uychi", "Yangiqo'rg'on",
  ],
  "Qashqadaryo": [
    "Qarshi shahri", "Shahrisabz shahri",
    "Chiroqchi", "Dehqonobod", "G'uzor", "Kasbi", "Kitob", "Koson", "Ko'kdala", "Mirishkor",
    "Muborak", "Nishon", "Qamashi", "Qarshi tumani", "Shahrisabz tumani", "Yakkabog'",
  ],
  "Surxondaryo": [
    "Termiz shahri",
    "Angor", "Bandixon", "Boysun", "Denov", "Jarqo'rg'on", "Muzrabot", "Oltinsoy", "Qiziriq",
    "Qumqo'rg'on", "Sariosiyo", "Sherobod", "Sho'rchi", "Termiz tumani", "Uzun",
  ],
  "Sirdaryo": [
    "Guliston shahri", "Shirin shahri", "Yangiyer shahri",
    "Boyovut", "Guliston tumani", "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod",
    "Sirdaryo tumani", "Xovos",
  ],
  "Jizzax": [
    "Jizzax shahri",
    "Arnasoy", "Baxmal", "Do'stlik", "Forish", "G'allaorol", "Mirzacho'l", "Paxtakor",
    "Sharof Rashidov", "Yangiobod", "Zafarobod", "Zarbdor", "Zomin",
  ],
  "Navoiy": [
    "Navoiy shahri", "Zarafshon shahri", "G'ozg'on shahri",
    "Karmana", "Konimex", "Navbahor", "Nurota", "Qiziltepa", "Tomdi", "Uchquduq", "Xatirchi",
  ],
  "Xorazm": [
    "Urganch shahri", "Xiva shahri",
    "Bog'ot", "Gurlan", "Hazorasp", "Qo'shko'pir", "Shovot", "Tuproqqal'a", "Urganch tumani",
    "Xiva tumani", "Xonqa", "Yangiariq", "Yangibozor",
  ],
  "Qoraqalpog'iston": [
    "Nukus shahri",
    "Amudaryo", "Beruniy", "Bo'zatov", "Chimboy", "Ellikqal'a", "Kegeyli", "Mo'ynoq",
    "Nukus tumani", "Qanliko'l", "Qo'ng'irot", "Qorao'zak", "Shumanay", "Taxiatosh",
    "Taxtako'pir", "To'rtko'l", "Xo'jayli",
  ],
};

// Older profiles stored the capital simply as "Toshkent".
const REGION_ALIAS = { Toshkent: "Toshkent shahri" };

const isUzbekistan = (country) =>
  !country || ["uzbekistan", "o'zbekiston", "узбекистан", "uz"].includes(String(country).trim().toLowerCase());

/** District list for a region, or null when there is no list (free text then). */
export function getDistrictsFor(country, region) {
  if (!region || !isUzbekistan(country)) return null;
  return UZ_DISTRICTS[REGION_ALIAS[region] || region] || null;
}

export default UZ_DISTRICTS;

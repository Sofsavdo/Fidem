"""AI conversation partners and the FIDEM assistant (temporary, launch phase).

While the app is young, the feed can look empty. These 20 characters (10
women, 10 men, ages 22-45) sit in the candidate list and always look online.
They reply in chat through Gemini, like a natural person of that character.

They are always labelled: `is_ai` is in every payload and the app shows
"🤖 AI" on the card, the profile and the chat. Their avatars are drawn
illustrations, never real people's photos. Chatting with them is free; it
never uses a paid unlock or the weekly free chat. They never claim to be
human, never agree to meet, and never swap contacts or talk about money.
The admin can switch them all off (Admin > Moderatsiya > Chat nazorati).
Off means they leave the feed and stop replying.

The assistant (id ai_assistant) answers questions about the app, helps with
the profile and first messages. It is pinned in Messages and not in the feed.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from datetime import timedelta

import core
from core import iso, now_utc, new_id, push_notif, manager

log = logging.getLogger("fidem.ai_personas")

ASSISTANT_ID = "ai_assistant"
AVATAR_VERSION = 1
DAILY_REPLY_CAP = 120          # AI replies one person can get per 24 h (cost guard)

# ---------- The characters ----------
# skin / hair / outfit / background colours drive the drawn avatar.
_SKIN = ["#f3cfb0", "#e9b896", "#dba27c", "#c98d66"]
_HAIR = ["#1d130e", "#2e1e15", "#4a2f1d", "#6b6b6b"]

PERSONAS: list[dict] = [
    # ---- women ----
    dict(slug="madina", name="Madina", gender="female", age=23, region="Toshkent", district="Chilonzor",
         marital="single", kids=0, height=163, weight=54, edu="Talaba", job="Tibbiyot talabasi (4-kurs)",
         rel="Islom", reloc=True, look=dict(skin=0, hair=1, scarf=False, outfit="#e5486b", bg=("#ffd6e2", "#ffeef3")),
         character="quvnoq, kitobxon, kelajakda pediatr bo'lmoqchi, oilasiga juda bog'langan, hazilni yaxshi ko'radi",
         bio="Tibbiyotda o'qiyman, bo'sh vaqtimda kitob o'qiyman va oshxonada yangi taomlar sinab ko'raman. Samimiy va mehribon insonni izlayapman."),
    dict(slug="nilufar", name="Nilufar", gender="female", age=27, region="Samarqand", district="Samarqand",
         marital="single", kids=0, height=160, weight=56, edu="Oliy", job="Ingliz tili o'qituvchisi",
         rel="Islom", reloc=False, look=dict(skin=1, hair=0, scarf=True, scarf_color="#6c8cd5", outfit="#3f5fae", bg=("#dce6ff", "#f1f5ff")),
         character="xotirjam, odobli, namozxon, oilaparvar, gapni o'ylab gapiradi, bolalarni yaxshi ko'radi",
         bio="Maktabda ingliz tilidan dars beraman. Oila men uchun eng muhim narsa. Diniy qadriyatlarni hurmat qiladigan, mas'uliyatli inson bilan oila qurmoqchiman."),
    dict(slug="dilnoza", name="Dilnoza", gender="female", age=31, region="Farg'ona", district="Marg'ilon",
         marital="single", kids=0, height=167, weight=58, edu="Oliy", job="Grafik dizayner",
         rel="Islom", reloc=True, look=dict(skin=1, hair=2, scarf=False, outfit="#2a9d8f", bg=("#d4f3ee", "#effbf8")),
         character="ijodkor, sayohatni sevadi, ochiq ko'ngil, biroz falsafiy, Marg'ilon atlasini yaxshi ko'radi",
         bio="Dizaynerman, ranglar va chiroyli narsalar bilan ishlayman. Sayohat qilishni, yangi joylarni ko'rishni yaxshi ko'raman. Hayotga ijobiy qaraydigan hamroh izlayman."),
    dict(slug="sevara", name="Sevara", gender="female", age=34, region="Toshkent", district="Yunusobod",
         marital="divorced", kids=1, height=165, weight=60, edu="Oliy", job="Buxgalter",
         rel="Islom", reloc=False, look=dict(skin=0, hair=0, scarf=False, outfit="#7a4ea3", bg=("#eadcff", "#f7f1ff")),
         character="jiddiy, ehtiyotkor, 6 yoshli o'g'li bor, ishonchni sekin beradi, lekin juda sodiq",
         bio="Ajrashganman, 6 yoshli o'g'lim bor. Hayot ko'p narsani o'rgatdi. Farzandimni ham qabul qiladigan, so'zining ustidan chiqadigan erkak bilan tanishmoqchiman."),
    dict(slug="malika", name="Malika", gender="female", age=25, region="Buxoro", district="Buxoro",
         marital="single", kids=0, height=158, weight=52, edu="O'rta maxsus", job="Hamshira",
         rel="Islom", reloc=True, look=dict(skin=2, hair=0, scarf=True, scarf_color="#d6a2b8", outfit="#b5678a", bg=("#ffe1ec", "#fff4f8")),
         character="mehribon, dindor, kamgap lekin samimiy, odamlarga yordam berishni yaxshi ko'radi",
         bio="Shifoxonada hamshiraman. Odamlarga yordam berish menga quvonch beradi. Iymonli, mehribon va oilasini e'zozlaydigan inson bilan tanishsam xursand bo'laman."),
    dict(slug="zilola", name="Zilola", gender="female", age=29, region="Andijon", district="Asaka",
         marital="single", kids=0, height=166, weight=57, edu="Oliy", job="Tadbirkor (kiyim do'koni)",
         rel="Islom", reloc=False, look=dict(skin=1, hair=1, scarf=False, outfit="#e07a1f", bg=("#ffe6cc", "#fff5ea")),
         character="shijoatli, tez gapiradi, maqsadli, o'z biznesi bor, mustaqil, lekin oilani ham xohlaydi",
         bio="O'z kiyim do'konim bor, ishimni sevaman. Maqsadli, o'zini hurmat qiladigan va meni ham qo'llab-quvvatlaydigan hamroh izlayapman."),
    dict(slug="gulnoza", name="Gulnoza", gender="female", age=38, region="Namangan", district="Chust",
         marital="widowed", kids=2, height=161, weight=63, edu="Oliy", job="Pediatr shifokor",
         rel="Islom", reloc=False, look=dict(skin=2, hair=0, scarf=True, scarf_color="#8fb996", outfit="#4f7d57", bg=("#e0f2e3", "#f3fbf4")),
         character="dono, sabrli, 2 farzandi bor, turmush o'rtog'i vafot etgan, hayotiy tajribasi katta, gaplari iliq",
         bio="Bolalar shifokoriman, ikki farzandim bor. Turmush o'rtog'im vafot etgan. Farzandlarimga ham ota bo'la oladigan, sabrli va diyonatli inson bilan tanishmoqchiman."),
    dict(slug="shahnoza", name="Shahnoza", gender="female", age=22, region="Xorazm", district="Urganch",
         marital="single", kids=0, height=159, weight=50, edu="Talaba", job="Iqtisodiyot talabasi",
         rel="Islom", reloc=True, look=dict(skin=0, hair=1, scarf=False, outfit="#3fa7d6", bg=("#d9f0ff", "#f0f9ff")),
         character="uyatchan, sodda, qisqa javob beradi, asta-sekin ochiladi, Xorazm taomlarini yaxshi ko'radi",
         bio="Iqtisodiyotda o'qiyman. Biroz uyatchanman, lekin yaqinroq tanishsangiz ochilib ketaman. Odobli va tushunadigan inson bilan tanishmoqchiman."),
    dict(slug="kamola", name="Kamola", gender="female", age=30, region="Qashqadaryo", district="Qarshi",
         marital="single", kids=0, height=168, weight=59, edu="Oliy", job="Dasturchi",
         rel="Islom", reloc=True, look=dict(skin=1, hair=2, scarf=False, outfit="#334155", bg=("#e2e8f0", "#f8fafc")),
         character="hazilkash, aqlli, texnologiyani yaxshi ko'radi, to'g'ridan-to'g'ri gapiradi, kofe ishqibozi",
         bio="Dasturchiman, kod yozish va yangi narsalarni o'rganishni yaxshi ko'raman. Hazilni tushunadigan, aqlli va samimiy suhbatdosh izlayman."),
    dict(slug="feruza", name="Feruza", gender="female", age=42, region="Toshkent", district="Mirzo Ulug'bek",
         marital="divorced", kids=2, height=164, weight=66, edu="O'rta maxsus", job="Oshpaz, o'z oshxonasi bor",
         rel="Islom", reloc=False, look=dict(skin=2, hair=3, scarf=False, outfit="#a0522d", bg=("#f6e2d3", "#fcf3ec")),
         character="hayotiy tajribali, ochiq, mazali ovqat pishiradi, farzandlari katta, xotirjam hayot istaydi",
         bio="Kichik oshxonam bor, ovqat pishirish mening hayotim. Farzandlarim katta bo'lib qolishdi. Endi tinch, bir-birini hurmat qiladigan oila qurmoqchiman."),
    # ---- men ----
    dict(slug="jasur", name="Jasur", gender="male", age=26, region="Toshkent", district="Chilonzor",
         marital="single", kids=0, height=180, weight=76, edu="Oliy", job="Dasturchi",
         rel="Islom", reloc=True, look=dict(skin=1, hair=0, beard=False, outfit="#2563eb", bg=("#dbe8ff", "#f0f6ff")),
         character="hazilkash, sportchi (futbol), IT-da ishlaydi, ochiq, kelajak rejalari bor",
         bio="Dasturchiman, hafta oxiri do'stlar bilan futbol o'ynayman. Kulishni yaxshi ko'raman. Samimiy va oilaparvar qiz bilan tanishmoqchiman."),
    dict(slug="bobur", name="Bobur", gender="male", age=29, region="Samarqand", district="Samarqand",
         marital="single", kids=0, height=178, weight=80, edu="Oliy", job="Stomatolog",
         rel="Islom", reloc=False, look=dict(skin=1, hair=0, beard=True, outfit="#0f766e", bg=("#d1f2ec", "#effbf8")),
         character="jiddiy, namozxon, mas'uliyatli, ota-onasini juda hurmat qiladi, so'zi bilan ishi bir",
         bio="Stomatologman. Namozimni o'qiyman, ota-onamni hurmat qilaman. Iymonli, odobli va oilaga sadoqatli qiz bilan halol oila qurish niyatim bor."),
    dict(slug="sardor", name="Sardor", gender="male", age=32, region="Farg'ona", district="Farg'ona",
         marital="single", kids=0, height=176, weight=84, edu="Oliy", job="Tadbirkor (qurilish)",
         rel="Islom", reloc=False, look=dict(skin=2, hair=0, beard=False, outfit="#1f2937", bg=("#e5e7eb", "#f9fafb")),
         character="ishbilarmon, ishonchli, oilaparvar, kam gapiradi lekin aniq, uy qurgan",
         bio="Qurilish sohasida o'z ishim bor, uyim tayyor. Endi oila qurish vaqti keldi deb o'ylayman. Mehribon va tushunadigan turmush o'rtog'i izlayman."),
    dict(slug="akmal", name="Akmal", gender="male", age=24, region="Andijon", district="Andijon",
         marital="single", kids=0, height=174, weight=68, edu="Talaba", job="Muhandislik talabasi",
         rel="Islom", reloc=True, look=dict(skin=0, hair=1, beard=False, outfit="#7c3aed", bg=("#ece4ff", "#f8f5ff")),
         character="uyatchan, romantik, she'riyatni yaxshi ko'radi, o'qishni bitirib ishlamoqchi",
         bio="Muhandislikda o'qiyman, oxirgi kursdaman. She'r o'qishni yaxshi ko'raman. Biroz uyatchanman, lekin niyatim jiddiy."),
    dict(slug="otabek", name="Otabek", gender="male", age=35, region="Toshkent", district="Yunusobod",
         marital="divorced", kids=1, height=182, weight=85, edu="Oliy", job="Bank xodimi",
         rel="Islom", reloc=False, look=dict(skin=1, hair=0, beard=True, outfit="#374151", bg=("#e2e8f0", "#f8fafc")),
         character="ehtiyotkor, mulohazali, qizi bor (8 yosh), xatolaridan saboq olgan, tinch oila istaydi",
         bio="Bankda ishlayman. Ajrashganman, 8 yoshli qizim bor. Bu safar shoshilmasdan, bir-birimizni yaxshi tanib, mustahkam oila qurmoqchiman."),
    dict(slug="rustam", name="Rustam", gender="male", age=28, region="Buxoro", district="Buxoro",
         marital="single", kids=0, height=177, weight=74, edu="Oliy", job="Tarix o'qituvchisi",
         rel="Islom", reloc=True, look=dict(skin=2, hair=1, beard=False, outfit="#b45309", bg=("#fdebd3", "#fff8ee")),
         character="kitobxon, xotirjam, Buxoro tarixi haqida soatlab gapira oladi, sabrli",
         bio="Maktabda tarixdan dars beraman. Buxoroning har bir ko'chasi haqida hikoya aytib bera olaman. Kitob va suhbatni yaxshi ko'radigan qiz bilan tanishmoqchiman."),
    dict(slug="doniyor", name="Doniyor", gender="male", age=31, region="Namangan", district="Namangan",
         marital="single", kids=0, height=175, weight=78, edu="O'rta maxsus", job="Logistika (yuk tashish)",
         rel="Islom", reloc=False, look=dict(skin=2, hair=0, beard=True, outfit="#15803d", bg=("#dcfce7", "#f2fdf5")),
         character="oddiy, mehnatkash, sodda gapiradi, ko'p sayohat qiladi (ish bilan), oilasi uchun hamma narsaga tayyor",
         bio="Yuk tashish bilan shug'ullanaman, ko'p yo'l yuraman. Oddiy, mehnatkash yigitman. Uyimni issiq qiladigan, sodiq qiz bilan oila qurmoqchiman."),
    dict(slug="sherzod", name="Sherzod", gender="male", age=40, region="Toshkent", district="Mirzo Ulug'bek",
         marital="widowed", kids=2, height=179, weight=86, edu="Oliy", job="Energetik muhandis",
         rel="Islom", reloc=False, look=dict(skin=1, hair=3, beard=True, outfit="#1e3a8a", bg=("#dbeafe", "#eff6ff")),
         character="mulohazali, iliq, ikki farzandini yolg'iz tarbiyalayapti, sabrli va g'amxo'r",
         bio="Muhandisman. Rafiqam vafot etgan, ikki farzandimni tarbiyalayapman. Farzandlarimga mehr bera oladigan, sabrli va oqila ayol bilan tanishmoqchiman."),
    dict(slug="aziz", name="Aziz", gender="male", age=27, region="Xorazm", district="Xiva",
         marital="single", kids=0, height=183, weight=79, edu="Oliy", job="Sport murabbiyi",
         rel="Islom", reloc=True, look=dict(skin=0, hair=0, beard=False, outfit="#dc2626", bg=("#ffe1e1", "#fff4f4")),
         character="quvnoq, faol, sog'lom turmush tarzi tarafdori, Xiva haqida faxr bilan gapiradi, energiyali",
         bio="Sport murabbiyiman, sog'lom hayot tarafdoriman. Xivadanman. Quvnoq, faol va hayotni sevadigan qiz bilan tanishmoqchiman."),
    dict(slug="farrux", name="Farrux", gender="male", age=45, region="Qashqadaryo", district="Shahrisabz",
         marital="divorced", kids=3, height=176, weight=88, edu="O'rta maxsus", job="Fermer, tadbirkor",
         rel="Islom", reloc=False, look=dict(skin=3, hair=3, beard=True, outfit="#6b4f2a", bg=("#efe4d2", "#faf6ef")),
         character="tajribali, an'anaviy qarashli, katta oilasi bor, bog' va dehqonchilikni sevadi, gapi salmoqli",
         bio="Fermerman, bog'im bor. Ajrashganman, farzandlarim katta. Uyimga fayz kiritadigan, an'analarimizni hurmat qiladigan ayol bilan oila qurmoqchiman."),
]

ASSISTANT = dict(
    slug="assistant", name="FIDEM yordamchisi", gender="female", age=25, region="Toshkent", district="",
    marital="single", kids=0, height=0, weight=0, edu="", job="AI yordamchi", rel="", reloc=None,
    look=dict(assistant=True), character="", bio="Ilova bo'yicha savollar, profil va birinchi xabar bo'yicha maslahatlar.",
)


def persona_id(p: dict) -> str:
    return ASSISTANT_ID if p is ASSISTANT else f"ai_{p['slug']}"


# ---------- Drawn avatars (SVG) ----------
def avatar_svg(p: dict) -> bytes:
    lk = p["look"]
    if lk.get("assistant"):
        return _assistant_svg()
    skin = _SKIN[lk["skin"]]
    hair = _HAIR[lk["hair"]]
    bg1, bg2 = lk["bg"]
    outfit = lk["outfit"]
    female = p["gender"] == "female"
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="800" height="1000">',
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{bg1}"/>'
        f'<stop offset="1" stop-color="{bg2}"/></linearGradient></defs>',
        '<rect width="400" height="500" fill="url(#g)"/>',
        '<circle cx="330" cy="80" r="60" fill="#ffffff" opacity=".35"/>',
        '<circle cx="60" cy="420" r="80" fill="#ffffff" opacity=".25"/>',
    ]
    if female and not lk.get("scarf"):   # long hair behind the head
        parts.append(f'<path d="M118,215 C110,120 165,100 200,102 C240,102 292,125 284,215 C292,290 300,340 304,380 L96,380 C100,330 110,290 118,215 Z" fill="{hair}"/>')
    parts.append(f'<path d="M50,500 C62,385 128,334 200,334 C272,334 338,385 350,500 Z" fill="{outfit}"/>')
    if lk.get("scarf"):
        sc = lk.get("scarf_color", "#888")
        parts.append(f'<path d="M108,232 C102,118 160,88 200,88 C240,88 298,118 292,232 C296,300 332,334 352,392 L48,392 C68,334 104,300 108,232 Z" fill="{sc}"/>')
    parts.append(f'<rect x="174" y="262" width="52" height="64" rx="18" fill="{skin}"/>')
    if not female:
        parts.append(f'<ellipse cx="129" cy="214" rx="11" ry="17" fill="{skin}"/><ellipse cx="271" cy="214" rx="11" ry="17" fill="{skin}"/>')
    parts.append(f'<ellipse cx="200" cy="208" rx="70" ry="84" fill="{skin}"/>')
    if lk.get("scarf"):
        sc = lk.get("scarf_color", "#888")
        parts.append(f'<path d="M128,176 C138,130 172,112 200,112 C228,112 262,130 272,176 C252,152 228,144 200,144 C172,144 148,152 128,176 Z" fill="{sc}" opacity=".95"/>')
    elif female:
        parts.append(f'<path d="M131,194 C134,138 170,118 204,118 C240,118 268,142 270,192 C246,160 218,150 198,152 C172,154 150,168 131,194 Z" fill="{hair}"/>')
    else:
        parts.append(f'<path d="M128,200 C122,132 164,108 204,108 C248,108 282,136 273,200 C266,166 246,150 204,148 C166,148 140,164 128,200 Z" fill="{hair}"/>')
        if lk.get("beard"):
            parts.append(f'<path d="M138,226 C146,288 176,306 200,306 C224,306 254,288 262,226 C252,258 230,270 200,270 C170,270 148,258 138,226 Z" fill="{hair}" opacity=".9"/>')
    # face
    parts += [
        '<path d="M164,190 Q176,182 188,190" stroke="#3a2a20" stroke-width="4" fill="none" stroke-linecap="round"/>',
        '<path d="M212,190 Q224,182 236,190" stroke="#3a2a20" stroke-width="4" fill="none" stroke-linecap="round"/>',
        '<ellipse cx="176" cy="210" rx="6" ry="7.5" fill="#2b1d16"/><ellipse cx="224" cy="210" rx="6" ry="7.5" fill="#2b1d16"/>',
        '<path d="M182,248 Q200,262 218,248" stroke="#8a3b3b" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
    ]
    if female:
        parts.append('<circle cx="158" cy="236" r="12" fill="#f19a9a" opacity=".35"/><circle cx="242" cy="236" r="12" fill="#f19a9a" opacity=".35"/>')
    parts += [
        '<rect x="306" y="440" width="78" height="40" rx="20" fill="#ffffff" opacity=".92"/>',
        '<text x="345" y="467" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" fill="#7c3aed">AI</text>',
        "</svg>",
    ]
    return "".join(parts).encode()


def _assistant_svg() -> bytes:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="800" height="1000">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ec4899"/>'
        '<stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>'
        '<rect width="400" height="500" fill="url(#g)"/>'
        '<rect x="110" y="150" width="180" height="150" rx="40" fill="#ffffff"/>'
        '<rect x="190" y="110" width="20" height="44" rx="10" fill="#ffffff"/><circle cx="200" cy="104" r="14" fill="#ffffff"/>'
        '<circle cx="160" cy="220" r="17" fill="#8b5cf6"/><circle cx="240" cy="220" r="17" fill="#8b5cf6"/>'
        '<path d="M168,262 Q200,282 232,262" stroke="#ec4899" stroke-width="8" fill="none" stroke-linecap="round"/>'
        '<path d="M200,400 C150,365 120,340 120,312 C120,295 134,284 150,284 C168,284 186,296 200,312 C214,296 232,284 250,284 C266,284 280,295 280,312 C280,340 250,365 200,400 Z" fill="#ffffff" opacity=".9"/>'
        '</svg>'
    ).encode()


# ---------- Seeding ----------
def _birth_date(age: int) -> str:
    today = now_utc().date()
    return today.replace(year=today.year - age, month=3, day=15).isoformat() if today.month > 3 else \
        today.replace(year=today.year - age - 1, month=3, day=15).isoformat()


def _doc(p: dict) -> dict:
    female = p["gender"] == "female"
    d = {
        "id": persona_id(p), "name": p["name"], "gender": p["gender"],
        "birth_date": _birth_date(p["age"]), "country": "Uzbekistan",
        "region": p["region"], "district": p["district"],
        "marital_status": p["marital"], "has_children": p["kids"] > 0, "children_count": p["kids"],
        "height_cm": p["height"], "weight_kg": p["weight"], "education": p["edu"],
        "profession": p["job"], "religion": p["rel"], "smoking": "no", "alcohol": "no",
        "relocation": p["reloc"], "bio": p["bio"],
        "looking_for": "Jiddiy munosabat, oila qurish",
        "search_gender": "male" if female else "female", "search_age_min": 18, "search_age_max": 60,
        "language": "uz", "onboarded": True, "terms_accepted": True,
        "is_ai": True, "ai_role": "assistant" if p is ASSISTANT else "candidate",
        "ai_character": p["character"], "plan": "free",
    }
    if p is ASSISTANT:
        d["hidden_profile"] = True   # never in the feed; pinned in Messages instead
    return d


async def _ensure_avatar(p: dict, existing: dict | None) -> dict:
    if existing and existing.get("ai_avatar_version") == AVATAR_VERSION and existing.get("photo_url"):
        return {}
    from storage import put_object
    pid = persona_id(p)
    res = await put_object(f"fidem/ai/{pid}_v{AVATAR_VERSION}.svg", avatar_svg(p), "image/svg+xml")
    await core.db.files.insert_one({
        "id": new_id(), "owner_id": pid, "storage_path": res["path"], "content_type": "image/svg+xml",
        "size": res.get("size", 0), "is_deleted": False, "is_public": True, "created_at": iso(now_utc()),
    })
    return {"photo_url": f"/api/files/{res['path']}", "ai_avatar_version": AVATAR_VERSION}


async def ensure_personas() -> None:
    """Create / refresh the AI characters (idempotent, runs at startup)."""
    for p in PERSONAS + [ASSISTANT]:
        pid = persona_id(p)
        try:
            existing = await core.db.users.find_one({"id": pid}, {"_id": 0, "photo_url": 1, "ai_avatar_version": 1})
            doc = _doc(p)
            doc.update(await _ensure_avatar(p, existing))
            doc["last_active"] = iso(now_utc())
            await core.db.users.update_one(
                {"id": pid},
                {"$set": doc, "$setOnInsert": {"created_at": iso(now_utc() - timedelta(days=random.randint(3, 40)))}},
                upsert=True,
            )
        except Exception:
            log.warning("could not set up AI persona %s", pid, exc_info=True)


# ---------- Settings (admin switch) ----------
_SETTINGS = {"at": 0.0, "on": None}
ENABLED_DEFAULT = os.environ.get("AI_PERSONAS", "1").strip().lower() not in ("0", "false", "off", "no")


async def enabled() -> bool:
    if _SETTINGS["on"] is not None and time.time() - _SETTINGS["at"] < 30:
        return _SETTINGS["on"]
    doc = await core.db.settings.find_one({"id": "ai_personas"}, {"_id": 0, "enabled": 1}) or {}
    val = bool(doc["enabled"]) if "enabled" in doc else ENABLED_DEFAULT
    _SETTINGS.update(at=time.time(), on=val)
    return val


def reset_settings_cache() -> None:
    _SETTINGS.update(at=0.0, on=None)


async def keep_online_loop() -> None:
    """The characters always look online (last_active refreshed)."""
    while True:
        try:
            if await enabled():
                await core.db.users.update_many({"is_ai": True}, {"$set": {"last_active": iso(now_utc())}})
        except Exception:
            log.warning("ai persona online refresh failed", exc_info=True)
        await asyncio.sleep(120)


# ---------- Replies ----------
_RULES = """Strict rules (never break them):
- You are an AI character inside the FIDEM app and the app labels you as "AI". If the person asks
  whether you are a real person, a bot or AI, answer honestly: you are FIDEM's AI conversation partner,
  and real people are in the candidates list. Never claim to be human.
- Never agree to meet in person, never give or ask for phone numbers, Telegram, Instagram, addresses,
  photos, money or card details. If asked, kindly say that as an AI you can't, and suggest real profiles.
- No sexual or vulgar content; keep Uzbek family values. Stay respectful even if they are rude.
- Write like a natural person in a messenger: 1-3 short sentences, no lists, no markdown,
  emojis rarely. Answer in the language the person writes in (Uzbek Latin by default, Russian or English if they use it).
- Keep the conversation going with a natural question now and then, but don't interrogate."""

_SCHEMA = {"type": "OBJECT", "properties": {"reply": {"type": "STRING"}}, "required": ["reply"]}

_ASSISTANT_FACTS = """You are "FIDEM yordamchisi", the AI helper of FIDEM, a marriage-intent dating
Telegram Mini App in Uzbekistan. Help with: how the app works, filling the profile, writing a good
first message, staying safe. Facts:
- Premium: 1 day 9,900 so'm, 15 days 49,900, 1 month 79,000; pay by card transfer, turns on right away, not a subscription.
- Women: Premium is free during the launch after the selfie check. Women can write after the selfie check.
- Selfie check: Men > Profil tasdiqlash; the app asks for a random hand gesture; AI or admin checks it.
- Contacts can't be sent in messages. Use the "Kontakt almashish" button: both selfie-verified,
  10+ messages each, the person asking has Premium, the other agrees.
- FIDEM never asks for money. Report anyone who asks for money or a card (chat menu > Shikoyat). Insults are blocked.
- Family contact: Premium users can request parents' contact on a profile.
- Characters marked "🤖 AI" in the list are AI conversation partners for practice, not real people.
- Human support: Telegram @Medik005.
Be warm and brief (2-4 sentences). If you don't know, say so and point to @Medik005."""


def _persona_prompt(p: dict, me: dict, history: list[dict], pid: str) -> str:
    if pid == ASSISTANT_ID:
        head = _ASSISTANT_FACTS
    else:
        kids = f"{p['kids']} farzandi bor" if p["kids"] else "farzandi yo'q"
        head = (
            f"You play {p['name']}, {p['age']}, {'woman' if p['gender'] == 'female' else 'man'} from "
            f"{p['region']}, Uzbekistan. Job: {p['job']}. Marital status: {p['marital']}, {kids}. "
            f"Character: {p['character']}. Profile text: {p['bio']}\n"
            "You are on FIDEM looking for a serious relationship and marriage, chatting with someone who wrote to you."
        )
    who = f"The person: {me.get('name', '')}, {core.age_from_birth(me.get('birth_date', '2000-01-01'))} y.o., {me.get('region', '')}."
    lines = []
    for m in history:
        speaker = "Siz" if m["from_user_id"] == pid else (me.get("name") or "Suhbatdosh")
        lines.append(f"{speaker}: {m.get('text', '')}")
    return f"{head}\n{_RULES}\n{who}\n\nConversation so far:\n" + "\n".join(lines) + "\n\nWrite your next message."


def _persona_by_id(pid: str) -> dict | None:
    if pid == ASSISTANT_ID:
        return ASSISTANT
    return next((p for p in PERSONAS if persona_id(p) == pid), None)


_pending: dict[str, asyncio.Task] = {}


def schedule_reply(uid: str, pid: str, chat_id: str) -> None:
    """Reply after a short, human-looking pause. A new message from the same
    person restarts the pause, so a burst of messages gets one answer."""
    old = _pending.get(chat_id)
    if old and not old.done():
        old.cancel()
    _pending[chat_id] = asyncio.ensure_future(_reply(uid, pid, chat_id))


async def _reply(uid: str, pid: str, chat_id: str) -> None:
    try:
        await asyncio.sleep(random.uniform(2.5, 6.0))      # "reading"
        p = _persona_by_id(pid)
        if not p or not await enabled():
            return
        since = iso(now_utc() - timedelta(hours=24))
        sent_today = await core.db.messages.count_documents(
            {"to_user_id": uid, "from_user_id": {"$regex": "^ai_"}, "created_at": {"$gte": since}},
        )
        if sent_today >= DAILY_REPLY_CAP:
            return
        me = await core.db.users.find_one({"id": uid}, {"_id": 0, "name": 1, "birth_date": 1, "region": 1})
        rows = await core.db.messages.find(
            {"chat_id": chat_id, "kind": "text"}, {"_id": 0, "from_user_id": 1, "text": 1},
        ).sort("created_at", -1).limit(16).to_list(16)
        history = list(reversed(rows))
        from ai_service import GEMINI_API_KEY, _gemini_json
        if not GEMINI_API_KEY:
            return
        res = await _gemini_json(_persona_prompt(p, me or {}, history, pid), [], _SCHEMA,
                                 max_tokens=400, timeout=25.0, thinking_budget=0)
        text = (res.get("reply") or "").strip()[:800]
        if not text:
            return
        # the same safety net as for people
        from ai_service import detect_contact_info, detect_money_request
        if detect_contact_info(text) or detect_money_request(text):
            return
        await asyncio.sleep(min(1.5 + len(text) / 30.0, 9.0))  # "typing"
        await core.db.messages.update_many({"chat_id": chat_id, "to_user_id": pid, "read": False}, {"$set": {"read": True}})
        msg = {
            "id": new_id(), "chat_id": chat_id, "from_user_id": pid, "to_user_id": uid,
            "text": text, "kind": "text", "created_at": iso(now_utc()), "read": False, "status": "chat",
        }
        await core.db.messages.insert_one(dict(msg))
        await manager.broadcast_chat([uid], {"type": "message", "data": msg})
        await push_notif(uid, "message", f"💬 {p['name']} (🤖 AI) sizga javob yozdi", link=f"/chat/{pid}")
    except asyncio.CancelledError:
        pass
    except Exception:
        log.warning("ai persona reply failed", exc_info=True)
    finally:
        if _pending.get(chat_id) is asyncio.current_task():
            _pending.pop(chat_id, None)

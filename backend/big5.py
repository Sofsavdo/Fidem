"""Big 5 (OCEAN) personality test — 20 questions across 5 traits.

Each trait has 4 questions. Answers: 1 (strongly disagree) ... 5 (strongly agree).
Scoring: each trait normalized to 0-100. 'r' marks reverse-scored items.
"""
from __future__ import annotations
from typing import Optional

BIG5_QUESTIONS = [
    # Openness (4)
    {"id": "o1", "trait": "openness", "reverse": False,
     "uz": "Yangi g'oyalar va san'atga qiziqaman.",
     "ru": "Я интересуюсь новыми идеями и искусством.",
     "en": "I am interested in new ideas and art."},
    {"id": "o2", "trait": "openness", "reverse": False,
     "uz": "Tasavvurim kuchli va ijodkorman.",
     "ru": "У меня богатое воображение и я творческий.",
     "en": "I have a vivid imagination and I am creative."},
    {"id": "o3", "trait": "openness", "reverse": True,
     "uz": "An'analarga qattiq amal qilishni afzal ko'raman.",
     "ru": "Предпочитаю строго следовать традициям.",
     "en": "I prefer strictly following traditions."},
    {"id": "o4", "trait": "openness", "reverse": False,
     "uz": "Sayohat qilish va yangi joylarni ko'rishni yoqtiraman.",
     "ru": "Люблю путешествовать и видеть новые места.",
     "en": "I like to travel and explore new places."},

    # Conscientiousness (4)
    {"id": "c1", "trait": "conscientiousness", "reverse": False,
     "uz": "Vazifalarni rejaga muvofiq, o'z vaqtida bajaraman.",
     "ru": "Выполняю задачи по плану и вовремя.",
     "en": "I complete tasks on time and as planned."},
    {"id": "c2", "trait": "conscientiousness", "reverse": False,
     "uz": "Tartibli va intizomli odamman.",
     "ru": "Я организованный и дисциплинированный.",
     "en": "I am organized and disciplined."},
    {"id": "c3", "trait": "conscientiousness", "reverse": True,
     "uz": "Ko'pincha vazifalarni keyinga qoldiraman.",
     "ru": "Часто откладываю дела на потом.",
     "en": "I often procrastinate on tasks."},
    {"id": "c4", "trait": "conscientiousness", "reverse": False,
     "uz": "Maqsadlarim aniq va ularga erishish uchun harakat qilaman.",
     "ru": "У меня ясные цели и я работаю над ними.",
     "en": "My goals are clear and I work toward them."},

    # Extraversion (4)
    {"id": "e1", "trait": "extraversion", "reverse": False,
     "uz": "Boshqalar bilan tanishishni yoqtiraman.",
     "ru": "Люблю знакомиться с новыми людьми.",
     "en": "I enjoy meeting new people."},
    {"id": "e2", "trait": "extraversion", "reverse": True,
     "uz": "Yolg'iz vaqt o'tkazishni ko'proq xohlayman.",
     "ru": "Предпочитаю проводить время в одиночестве.",
     "en": "I prefer to spend time alone."},
    {"id": "e3", "trait": "extraversion", "reverse": False,
     "uz": "Davralarda jonli va gapdon bo'laman.",
     "ru": "В компании я общительный и активный.",
     "en": "I am lively and talkative in groups."},
    {"id": "e4", "trait": "extraversion", "reverse": False,
     "uz": "Tadbirlar va to'planishlarni yoqtiraman.",
     "ru": "Мне нравятся события и собрания.",
     "en": "I enjoy events and gatherings."},

    # Agreeableness (4)
    {"id": "a1", "trait": "agreeableness", "reverse": False,
     "uz": "Boshqalarga yordam berishga tayyorman.",
     "ru": "Я готов помогать другим.",
     "en": "I am willing to help others."},
    {"id": "a2", "trait": "agreeableness", "reverse": False,
     "uz": "Mehribon va xayrxohman.",
     "ru": "Я добрый и доброжелательный.",
     "en": "I am kind and benevolent."},
    {"id": "a3", "trait": "agreeableness", "reverse": True,
     "uz": "Ba'zan boshqalarga qattiq munosabatda bo'laman.",
     "ru": "Иногда бываю жёстким с другими.",
     "en": "I am sometimes harsh with others."},
    {"id": "a4", "trait": "agreeableness", "reverse": False,
     "uz": "Murosa va kelishuvga moyilman.",
     "ru": "Склонен к компромиссу.",
     "en": "I am inclined toward compromise."},

    # Neuroticism (4)
    {"id": "n1", "trait": "neuroticism", "reverse": False,
     "uz": "Ko'pincha tashvishlanaman yoki xavotirlanaman.",
     "ru": "Часто волнуюсь или переживаю.",
     "en": "I often feel anxious or worried."},
    {"id": "n2", "trait": "neuroticism", "reverse": False,
     "uz": "Stress holatlarida o'zimni boshqarish qiyin.",
     "ru": "Мне трудно справляться со стрессом.",
     "en": "I find it hard to handle stress."},
    {"id": "n3", "trait": "neuroticism", "reverse": True,
     "uz": "Hissiyotlarim barqaror va xotirjamman.",
     "ru": "У меня стабильные эмоции и я спокоен.",
     "en": "My emotions are stable and I am calm."},
    {"id": "n4", "trait": "neuroticism", "reverse": False,
     "uz": "Tezda xafa bo'laman yoki asabiylashaman.",
     "ru": "Быстро обижаюсь или раздражаюсь.",
     "en": "I get upset or irritated quickly."},
]

TRAIT_LABELS = {
    "uz": {
        "openness": "Yangilikka ochiqlik",
        "conscientiousness": "Mas'uliyatlilik",
        "extraversion": "Ekstraversiya",
        "agreeableness": "Xushmuomalalik",
        "neuroticism": "Emotsional sezgirlik",
    },
    "ru": {
        "openness": "Открытость новому",
        "conscientiousness": "Ответственность",
        "extraversion": "Экстраверсия",
        "agreeableness": "Доброжелательность",
        "neuroticism": "Эмоциональность",
    },
    "en": {
        "openness": "Openness",
        "conscientiousness": "Conscientiousness",
        "extraversion": "Extraversion",
        "agreeableness": "Agreeableness",
        "neuroticism": "Neuroticism",
    },
}


def get_questions_localized(lang: str = "uz") -> list[dict]:
    out = []
    for q in BIG5_QUESTIONS:
        out.append({
            "id": q["id"],
            "trait": q["trait"],
            "question": q.get(lang, q["uz"]),
            "scale": [
                {"value": 1, "label": {"uz": "Mutlaqo qo'shilmayman", "ru": "Совсем не согласен", "en": "Strongly disagree"}.get(lang)},
                {"value": 2, "label": {"uz": "Qo'shilmayman", "ru": "Не согласен", "en": "Disagree"}.get(lang)},
                {"value": 3, "label": {"uz": "Neytral", "ru": "Нейтрально", "en": "Neutral"}.get(lang)},
                {"value": 4, "label": {"uz": "Qo'shilaman", "ru": "Согласен", "en": "Agree"}.get(lang)},
                {"value": 5, "label": {"uz": "Mutlaqo qo'shilaman", "ru": "Полностью согласен", "en": "Strongly agree"}.get(lang)},
            ],
        })
    return out


def compute_big5_scores(answers: dict[str, int]) -> dict[str, int]:
    """Returns {"openness": 0-100, "conscientiousness": 0-100, ...}."""
    traits: dict[str, list[int]] = {}
    for q in BIG5_QUESTIONS:
        a = answers.get(q["id"])
        if a is None:
            continue
        try:
            v = int(a)
        except Exception:
            continue
        if not (1 <= v <= 5):
            continue
        if q["reverse"]:
            v = 6 - v
        traits.setdefault(q["trait"], []).append(v)
    scores = {}
    for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
        vals = traits.get(trait, [])
        if not vals:
            scores[trait] = 0
        else:
            # raw average (1..5) → 0..100
            avg = sum(vals) / len(vals)
            scores[trait] = round((avg - 1) / 4 * 100)
    return scores


def big5_compatibility(a: dict[str, int], b: dict[str, int]) -> int:
    """Compatibility 0-100 from two Big 5 score dicts.
    Research shows SIMILARITY is a stronger predictor than complementarity for long-term match.
    """
    if not a or not b:
        return 0
    traits = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")
    total = 0
    cnt = 0
    for t in traits:
        if t in a and t in b:
            diff = abs(a[t] - b[t])
            # Convert diff to similarity: 0 diff = 100, 100 diff = 0
            sim = max(0, 100 - diff)
            # Slight bonus for low neuroticism on both sides
            if t == "neuroticism" and a[t] < 50 and b[t] < 50:
                sim = min(100, sim + 10)
            total += sim
            cnt += 1
    return round(total / cnt) if cnt else 0

"""Match %: different people get different scores; no free constant boosts."""
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

from routers.candidates_r import compute_ai_match  # noqa: E402
from services import compute_match  # noqa: E402

ME = dict(gender="male", birth_date="1994-05-01", region="Toshkent", district="Chilonzor", search_gender="female",
          search_age_min=22, search_age_max=32, marital_status="single", has_children=False, height_cm=178,
          religion="Islom", education="Oliy", smoking="no", alcohol="no", looking_for="Jiddiy munosabat, oila qurish",
          bio="Dasturchiman, sport va kitob o'qishni yaxshi ko'raman", profession="Dasturchi", plan="vip")


def _people(n=20, seed=3):
    rnd = random.Random(seed)
    for _ in range(n):
        yield dict(gender="female", birth_date=f"{rnd.randint(1986, 2004)}-05-15", region=rnd.choice(["Toshkent", "Samarqand", "Buxoro", "Andijon"]),
                   search_gender="male", search_age_min=rnd.choice([22, 25, 28]), search_age_max=rnd.choice([33, 38, 45]),
                   marital_status=rnd.choice(["single", "single", "divorced"]), has_children=rnd.random() < 0.2,
                   height_cm=rnd.choice([0, 158, 165, 172]), religion=rnd.choice(["Islom", "Islom", ""]),
                   education=rnd.choice(["Oliy", "O'rta maxsus", ""]), smoking=rnd.choice(["no", ""]), alcohol=rnd.choice(["no", "sometimes"]),
                   looking_for="Jiddiy munosabat, oila qurish", bio=rnd.choice(["Shifokorman", "Oilaparvar, mehribon", ""]))


def test_scores_are_spread_out_not_one_number():
    scores = [compute_ai_match(ME, c, "uz")[0] for c in _people()]
    assert len(set(scores)) >= 10
    assert max(scores) - min(scores) >= 20


def test_no_free_boost_for_missing_activity_or_reply_data():
    c = next(_people(1))
    base, _ = compute_match(ME, c, "uz")
    ai, reasons = compute_ai_match({**ME, "plan": "free"}, c, "uz")
    assert ai == base and "Faollik vaqti mos" not in reasons and "Javob tezligi mos" not in reasons


def test_closer_match_scores_higher():
    near = dict(ME, gender="female", birth_date="1997-05-01", search_gender="male", search_age_min=25, search_age_max=35, height_cm=165)
    far = dict(near, region="Xorazm", district="", birth_date="1986-05-01", religion="", has_children=True, marital_status="divorced", smoking="yes")
    assert compute_match(ME, near)[0] > compute_match(ME, far)[0] + 25

"""Regression guard for the chat_r.py boot-crash class of bug.

`from __future__ import annotations` turns every type hint into a string
that is only evaluated lazily. FastAPI resolves them via
`typing.get_type_hints()` at route-registration time (app startup) — so a
type hint referencing a name that was never imported (e.g. `Optional[str]`
without `from typing import Optional`) imports fine but crashes the whole
app at boot. This test imports every router/module and forces resolution
of every function's annotations, catching that class of bug at test time
instead of at deploy time.
"""
from __future__ import annotations

import importlib
import os
import sys
import typing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

MODULES = [
    "core", "auth", "models", "services", "big5", "storage", "geo", "winback", "lifecycle",
    "routers.admin_r", "routers.ai_r", "routers.announcements_r", "routers.auth_r", "routers.boost_analytics_r",
    "routers.candidates_r", "routers.chat_r",
    "routers.concierge_r", "routers.face_r", "routers.family_r",
    "routers.growth_r", "routers.location_r", "routers.payments_r", "routers.personality_r",
    "routers.picks_r", "routers.prompts_r",
    "routers.settings_r", "routers.stories_r", "routers.telegram_r",
    "routers.withdrawals_r",
]


def test_all_backend_modules_import_cleanly():
    for modname in MODULES:
        importlib.import_module(modname)


def test_all_function_annotations_resolve():
    """Forces typing.get_type_hints() on every module-level callable, exactly
    what FastAPI does when registering routes — surfaces NameErrors from
    unimported type hints before they can crash the app at boot."""
    errors = []
    for modname in MODULES:
        mod = importlib.import_module(modname)
        for name in dir(mod):
            obj = getattr(mod, name)
            if callable(obj) and hasattr(obj, "__annotations__") and getattr(obj, "__module__", None) == modname:
                try:
                    typing.get_type_hints(obj)
                except Exception as e:
                    errors.append(f"{modname}.{name}: {type(e).__name__}: {e}")
    assert not errors, "Unresolvable type hints found:\n" + "\n".join(errors)

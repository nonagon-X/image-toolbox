"""
Translations for Toolbox.

Write every visible text in English and wrap it in tr():
    tr("Choose folder…")
    tr("Found {n} file(s).", n=num(4))
Polish texts live in _lang_pl.py (English text → Polish text). Anything missing
there simply shows in English. To add a language, create _lang_xx.py with a
dict named TEXTS and add it to LANGS below.
"""

import importlib
import json
import os
import sys
from pathlib import Path

LANGS = {"en": "English", "pl": "Polski"}
SETTINGS_FILE = Path(os.environ.get("APPDATA", Path.home())) / "Toolbox" / "settings.json"

_lang = "en"
_texts = {}


def _detect():
    if sys.platform == "win32":
        try:
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x15:  # Polish
                return "pl"
        except Exception:
            pass
    import locale
    loc = (locale.getlocale()[0] or "").lower()
    return "pl" if loc.startswith(("pl", "polish")) else "en"


def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_setting(key, value):
    data = load_settings()
    data[key] = value
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def set_language(code, remember=True):
    global _lang, _texts
    _lang = code if code in LANGS else "en"
    _texts = {}
    if _lang != "en":
        try:
            _texts = importlib.import_module(f"_lang_{_lang}").TEXTS
        except Exception:
            _texts = {}
    if remember:
        save_setting("language", _lang)


def language():
    return _lang


def init():
    set_language(load_settings().get("language") or _detect(), remember=False)


def tr(text, **values):
    s = _texts.get(text, text)
    return s.format(**values) if values else s


def num(n):
    """Whole number with thousands separators (1,200 / 1 200)."""
    s = f"{n:,}"
    return s.replace(",", " ") if _lang == "pl" else s


def dec(x, places=1):
    """Decimal number (5.0 / 5,0)."""
    s = f"{x:.{places}f}"
    return s.replace(".", ",") if _lang == "pl" else s

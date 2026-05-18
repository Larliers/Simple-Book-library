from __future__ import annotations

import json
from pathlib import Path


class LanguageManager:
    def __init__(self) -> None:
        self._current_language = "en"
        self._catalog_cache: dict[str, dict[str, str]] = {}
        self._locales_dir = Path(__file__).parent / "locales"

    @property
    def current_language(self) -> str:
        return self._current_language

    def set_language(self, language_code: str) -> None:
        normalized = (language_code or "en").strip().lower()
        self._current_language = normalized if normalized else "en"

    def text(self, key: str, english_text: str) -> str:
        if self._current_language == "en":
            return english_text
        catalog = self._load_catalog(self._current_language)
        return catalog.get(key, english_text)

    def _load_catalog(self, language_code: str) -> dict[str, str]:
        if language_code in self._catalog_cache:
            return self._catalog_cache[language_code]

        file_path = self._locales_dir / f"{language_code}.json"
        if not file_path.exists():
            self._catalog_cache[language_code] = {}
            return {}

        try:
            data = json.loads(file_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            data = {}

        if not isinstance(data, dict):
            data = {}
        self._catalog_cache[language_code] = {str(k): str(v) for k, v in data.items()}
        return self._catalog_cache[language_code]


language_manager = LanguageManager()


def tr(key: str, english_text: str) -> str:
    return language_manager.text(key, english_text)

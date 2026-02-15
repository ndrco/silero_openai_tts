from dataclasses import dataclass
import re

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")
TOKEN_RE = re.compile(r"[A-Za-z]+|[А-Яа-яЁё]+|[^A-Za-zА-Яа-яЁё]+")


@dataclass(frozen=True)
class TextSegment:
    text: str
    lang: str  # "ru" | "en"


class LanguageAwareRouter:
    """Detects text language and splits mixed text into language segments."""

    @staticmethod
    def detect_token_language(token: str) -> str | None:
        if CYRILLIC_RE.search(token):
            return "ru"
        if LATIN_RE.search(token):
            return "en"
        return None

    def split(self, text: str) -> list[TextSegment]:
        raw = text or ""
        if not raw.strip():
            return []

        tokens = TOKEN_RE.findall(raw)
        segments: list[TextSegment] = []
        current_lang: str | None = None
        current_parts: list[str] = []

        for token in tokens:
            token_lang = self.detect_token_language(token)
            if token_lang is None:
                current_parts.append(token)
                continue

            if current_lang is None:
                current_lang = token_lang
                current_parts.append(token)
                continue

            if token_lang == current_lang:
                current_parts.append(token)
                continue

            segment_text = "".join(current_parts).strip()
            if segment_text:
                segments.append(TextSegment(text=segment_text, lang=current_lang))

            current_lang = token_lang
            current_parts = [token]

        segment_text = "".join(current_parts).strip()
        if segment_text:
            segments.append(TextSegment(text=segment_text, lang=current_lang or "ru"))

        return segments

    def detect(self, text: str) -> str:
        segments = self.split(text)
        langs = {segment.lang for segment in segments}
        if len(langs) > 1:
            return "mixed"
        if "en" in langs:
            return "en"
        return "ru"

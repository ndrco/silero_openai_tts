import re

from app.text.numbers import expand_numbers, expand_numbers_en
from app.text.transliterate import transliterate_latin_to_cyrillic

# URL заменяем на слово «ссылка»; подпись перед URL (GitHub: и т.п.) оставляем для озвучки
URL_RE = re.compile(
    r"https?://[^\s<>\[\]()]+|www\.[^\s<>\[\]()]+",
    re.IGNORECASE,
)


def replace_urls(text: str) -> str:
    """Заменяет только URL в тексте на слово «ссылка» для озвучки. Подпись (например GitHub:) остаётся."""
    return URL_RE.sub(" ссылка ", text)


class TextNormalizer:
    def __init__(self, transliterate_latin: bool = True, expand_numeric: bool = True, expand_numeric_lang: str = "ru"):
        self.transliterate_latin = transliterate_latin
        self.expand_numeric = expand_numeric
        self.expand_numeric_lang = expand_numeric_lang  # "ru" | "en"

    def run(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        t = replace_urls(t)
        if self.expand_numeric:
            if self.expand_numeric_lang == "en":
                t = expand_numbers_en(t)
            else:
                t = expand_numbers(t)
        if self.transliterate_latin:
            t = transliterate_latin_to_cyrillic(t)
        t = " ".join(t.split())
        return t

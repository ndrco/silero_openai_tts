import re

from app.text.numbers import expand_numbers, expand_numbers_en
from app.text.transliterate import transliterate_latin_to_cyrillic

# Replace URLs with the word "link"; keep any label before URL (GitHub:, etc.) for TTS
URL_RE = re.compile(
    r"https?://[^\s<>\[\]()]+|www\.[^\s<>\[\]()]+",
    re.IGNORECASE,
)


def replace_urls(text: str) -> str:
    """Replaces only URLs in text with the word "link" for TTS. Labels (e.g., GitHub:) stay intact."""
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

import re

from app.text.numbers import expand_numbers, expand_numbers_en
from app.text.transliterate import transliterate_latin_to_cyrillic

# Replace URLs with the word "link"; keep any label before URL (GitHub:, etc.) for TTS
URL_RE = re.compile(
    r"https?://[^\s<>\[\]()]+|www\.[^\s<>\[\]()]+",
    re.IGNORECASE,
)

_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_FORMAT_QUERY_RE = re.compile(r"\?format=[^\s\"']+", re.IGNORECASE)
_PERCENT_PLACEHOLDER_RE = re.compile(r"%[a-zA-Zа-яА-Я]+")
_BACKTICKS_RE = re.compile(r"`+")
_MARKDOWN_DECORATORS_RE = re.compile(r"(^|\n)\s{0,3}(?:[#>*-]+\s+)")


_TECHNICAL_SYMBOL_WORDS_RU = {
    "/": " слэш ",
    "%": " процент ",
    "+": " плюс ",
    "=": " равно ",
    ":": " двоеточие ",
}

_RU_ALLOWED_RE = re.compile(r"[^\w\s.,!?\-—…]", re.UNICODE)
_EN_ALLOWED_RE = re.compile(r"[^\w\s.,!?;:'\"()\-—…/%+=]", re.UNICODE)


def replace_urls(text: str) -> str:
    """Replaces only URLs in text with the word "link" for TTS. Labels (e.g., GitHub:) stay intact."""
    return URL_RE.sub(" link ", text)


def strip_unsupported_symbols(text: str, lang: str = "ru") -> str:
    """Removes symbols that commonly break Silero symbol lookup (e.g. '^')."""
    if lang == "en":
        return _EN_ALLOWED_RE.sub(" ", text)
    return _RU_ALLOWED_RE.sub(" ", text)


def verbalize_technical_symbols_ru(text: str) -> str:
    """Converts technical symbols to RU words so they are spoken, not dropped."""
    out = text or ""
    for symbol, word in _TECHNICAL_SYMBOL_WORDS_RU.items():
        out = out.replace(symbol, word)
    return " ".join(out.split())


def clean_markdown_for_tts(text: str) -> str:
    """Removes code/markdown artifacts that often break RU Silero parsing."""
    t = text or ""
    t = _CODE_BLOCK_RE.sub(" ", t)
    t = _MARKDOWN_LINK_RE.sub(lambda m: m.group(1), t)
    t = _FORMAT_QUERY_RE.sub(" ", t)
    t = _PERCENT_PLACEHOLDER_RE.sub(" ", t)
    t = _BACKTICKS_RE.sub(" ", t)
    t = _MARKDOWN_DECORATORS_RE.sub("\\1", t)
    return " ".join(t.split())


class TextNormalizer:
    def __init__(self, transliterate_latin: bool = True, expand_numeric: bool = True, expand_numeric_lang: str = "ru"):
        self.transliterate_latin = transliterate_latin
        self.expand_numeric = expand_numeric
        self.expand_numeric_lang = expand_numeric_lang  # "ru" | "en"

    def run(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        if self.expand_numeric:
            if self.expand_numeric_lang == "en":
                t = expand_numbers_en(t)
            else:
                t = expand_numbers(t)
        if self.transliterate_latin:
            t = transliterate_latin_to_cyrillic(t)
        if self.expand_numeric_lang == "ru":
            t = verbalize_technical_symbols_ru(t)
        t = strip_unsupported_symbols(t, lang=self.expand_numeric_lang)
        t = " ".join(t.split())
        return t

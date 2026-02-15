from app.text.numbers import expand_numbers
from app.text.transliterate import transliterate_latin_to_cyrillic


class TextNormalizer:
    def __init__(self, transliterate_latin: bool = True, expand_numeric: bool = True):
        self.transliterate_latin = transliterate_latin
        self.expand_numeric = expand_numeric

    def run(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        if self.expand_numeric:
            t = expand_numbers(t)
        if self.transliterate_latin:
            t = transliterate_latin_to_cyrillic(t)
        t = " ".join(t.split())
        return t

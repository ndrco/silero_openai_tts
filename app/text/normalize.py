from app.text.numbers import expand_numbers
from app.text.transliterate import transliterate_latin_to_cyrillic


class TextNormalizer:
    def __init__(self, transliterate_latin: bool = True):
        self.transliterate_latin = transliterate_latin

    def run(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        t = expand_numbers(t)
        if self.transliterate_latin:
            t = transliterate_latin_to_cyrillic(t)
        t = " ".join(t.split())
        return t

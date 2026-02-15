"""Latin-to-Cyrillic transliteration to pronounce English words with Russian TTS (Silero)."""
import re

# Latin → Cyrillic (Russian-style pronunciation: hello → "khello" style)
_LATIN_TO_CYRILLIC = str.maketrans(
    "abvgdezijklmnoprstufhcABVGDEZIJKLMNOPRSTUFHC",
    "абвгдезийклмнопрстуфхцАБВГДЕЗИЙКЛМНОПРСТУФХЦ",
)
# Extra letters: q→k, w→v, y→y (x is handled separately as x→ks)
_LATIN_TO_CYRILLIC.update(str.maketrans("qQwWyY", "кКвВйЙ"))

# Digraphs (processed before single letters so ch→ch-like, sh→sh-like)
_LATIN_DIGRAPHS = [
    ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
    ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
    ("zh", "ж"), ("Zh", "Ж"), ("ZH", "Ж"),
    ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
    ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
    ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
    ("ye", "е"), ("Ye", "Е"), ("YE", "Е"),  # yes → "yes" pronounced as "es"
    ("ts", "ц"), ("Ts", "Ц"), ("TS", "Ц"),
]


def _transliterate_word(word: str) -> str:
    """Converts one token (Latin letters only) to Cyrillic."""
    s = word.replace("x", "кс").replace("X", "Кс")
    for lat, cyr in _LATIN_DIGRAPHS:
        s = s.replace(lat, cyr)
    return s.translate(_LATIN_TO_CYRILLIC)


def transliterate_latin_to_cyrillic(text: str) -> str:
    """
    Replaces words made of Latin letters with Cyrillic transliteration.
    The rest of the text (Cyrillic, digits, punctuation) remains unchanged.
    """
    # Tokens: sequences of Latin letters (a-zA-Z)
    def repl(m: re.Match) -> str:
        return _transliterate_word(m.group(0))

    return re.sub(r"[a-zA-Z]+", repl, text)

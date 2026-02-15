"""Транслитерация латиницы в кириллицу для озвучки английских слов русской TTS (Silero)."""
import re

# Латиница → кириллица (озвучивание по-русски: hello → хеллоу)
_LATIN_TO_CYRILLIC = str.maketrans(
    "abvgdezijklmnoprstufhcABVGDEZIJKLMNOPRSTUFHC",
    "абвгдезийклмнопрстуфхцАБВГДЕЗИЙКЛМНОПРСТУФХЦ",
)
# Доп. буквы: q→к, w→в, y→й (x обрабатываем отдельно как x→кс)
_LATIN_TO_CYRILLIC.update(str.maketrans("qQwWyY", "кКвВйЙ"))

# Диграфы (обрабатываем до одиночных, чтобы ch→ч, sh→ш)
_LATIN_DIGRAPHS = [
    ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
    ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
    ("zh", "ж"), ("Zh", "Ж"), ("ZH", "Ж"),
    ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
    ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
    ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
    ("ye", "е"), ("Ye", "Е"), ("YE", "Е"),  # yes → ес
    ("ts", "ц"), ("Ts", "Ц"), ("TS", "Ц"),
]


def _transliterate_word(word: str) -> str:
    """Один токен (только латинские буквы) в кириллицу."""
    s = word.replace("x", "кс").replace("X", "Кс")
    for lat, cyr in _LATIN_DIGRAPHS:
        s = s.replace(lat, cyr)
    return s.translate(_LATIN_TO_CYRILLIC)


def transliterate_latin_to_cyrillic(text: str) -> str:
    """
    Заменяет слова из латинских букв на кириллическую транслитерацию.
    Остальной текст (кириллица, цифры, пунктуация) не меняется.
    """
    # Токены: последовательности латинских букв (a-zA-Z)
    def repl(m: re.Match) -> str:
        return _transliterate_word(m.group(0))

    return re.sub(r"[a-zA-Z]+", repl, text)

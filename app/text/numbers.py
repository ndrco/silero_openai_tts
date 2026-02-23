import re
from num2words import num2words
from app.text.morph import agree_word_with_number, match_case

NUM_NOUN_RE = re.compile(r"(?<!\w)(\d{1,18})\s+([А-Яа-яЁё]+)(?!\w)")
PERCENT_RE = re.compile(r"(?<!\w)(\d{1,18})\s*%(?!\w)")
RUBLE_RE = re.compile(r"(?<!\w)(\d{1,18})\s*(₽|руб\.?|рубля|рублей|рубль)(?!\w)", re.IGNORECASE)
STANDALONE_INT_RE = re.compile(r"(?<!\d\.)\b(\d{1,18})\b(?![.:]\d)")

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
VERSION_RE = re.compile(r"\bv\d+(?:\.\d+){1,3}\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b")
TZ_OFFSET_RE = re.compile(r"\b(UTC|GMT)\s*([+-])\s*(\d{1,2})\b", re.IGNORECASE)
UNARY_SIGN_NUM_RE = re.compile(r"(?<!\w)([+-])\s*(\d+(?:[.,]\d+)?)\b")
RANGE_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\b")
DECIMAL_RE = re.compile(r"\b(\d+)[.,](\d+)\b")

FRACTION_DENOMINATORS = {
    1: "десятых",
    2: "сотых",
    3: "тысячных",
    4: "десятитысячных",
    5: "стотысячных",
    6: "миллионных",
}

def _num_to_words_ru(n: int) -> str:
    return num2words(n, lang="ru").replace("-", " ")


def _decimal_to_words_ru(int_part: str, frac_part: str) -> str:
    int_words = _num_to_words_ru(int(int_part))
    frac_int = int(frac_part)
    if frac_int == 0:
        return f"{int_words} целых ноль"

    frac_words = _num_to_words_ru(frac_int)
    denom = FRACTION_DENOMINATORS.get(len(frac_part))
    if denom is None:
        return f"{int_words} запятая {frac_words}"
    return f"{int_words} целых {frac_words} {denom}"


def _protect_patterns(text: str) -> tuple[str, dict[str, str]]:
    protected_map: dict[str, str] = {}
    idx = 0

    def _replace(match: re.Match) -> str:
        nonlocal idx
        key = f"__PROTECTED_{idx}__"
        idx += 1
        protected_map[key] = match.group(0)
        return key

    for pattern in (IP_RE, VERSION_RE, DATE_RE):
        text = pattern.sub(_replace, text)
    return text, protected_map


def _restore_patterns(text: str, protected_map: dict[str, str]) -> str:
    for key, original in protected_map.items():
        text = text.replace(key, original)
    return text


def _pre_expand_ru_patterns(text: str) -> str:
    text, protected_map = _protect_patterns(text)

    def repl_time(m: re.Match) -> str:
        hh = int(m.group(1))
        mm = int(m.group(2))
        ss = m.group(3)
        parts = [f"{_num_to_words_ru(hh)} часов", f"{_num_to_words_ru(mm)} минут"]
        if ss is not None:
            parts.append(f"{_num_to_words_ru(int(ss))} секунд")
        return " ".join(parts)

    text = TIME_RE.sub(repl_time, text)

    def repl_tz(m: re.Match) -> str:
        zone = m.group(1).upper()
        sign = "плюс" if m.group(2) == "+" else "минус"
        offset_words = _num_to_words_ru(int(m.group(3)))
        return f"{zone} {sign} {offset_words}"

    text = TZ_OFFSET_RE.sub(repl_tz, text)

    def repl_unary_sign(m: re.Match) -> str:
        sign = "плюс" if m.group(1) == "+" else "минус"
        return f"{sign} {m.group(2)}"

    text = UNARY_SIGN_NUM_RE.sub(repl_unary_sign, text)

    def repl_range(m: re.Match) -> str:
        return f"от {m.group(1)} до {m.group(2)}"

    text = RANGE_RE.sub(repl_range, text)

    def repl_decimal(m: re.Match) -> str:
        return _decimal_to_words_ru(m.group(1), m.group(2))

    text = DECIMAL_RE.sub(repl_decimal, text)
    return _restore_patterns(text, protected_map)

def expand_numbers(text: str) -> str:
    text = _pre_expand_ru_patterns(text)

    def repl_num_noun(m: re.Match) -> str:
        n = int(m.group(1))
        noun = m.group(2)
        noun2 = agree_word_with_number(noun.lower(), n)
        noun2 = match_case(noun, noun2)
        return f"{_num_to_words_ru(n)} {noun2}"

    text = NUM_NOUN_RE.sub(repl_num_noun, text)

    def repl_percent(m: re.Match) -> str:
        n = int(m.group(1))
        noun2 = agree_word_with_number("процент", n)
        return f"{_num_to_words_ru(n)} {noun2}"

    text = PERCENT_RE.sub(repl_percent, text)

    def repl_ruble(m: re.Match) -> str:
        n = int(m.group(1))
        noun2 = agree_word_with_number("рубль", n)
        return f"{_num_to_words_ru(n)} {noun2}"

    text = RUBLE_RE.sub(repl_ruble, text)

    def repl_standalone(m: re.Match) -> str:
        n = int(m.group(1))
        return _num_to_words_ru(n)

    text = STANDALONE_INT_RE.sub(repl_standalone, text)
    return text


# English: standalone numbers and #N
HASH_NUM_RE = re.compile(r"#(\d{1,18})\b")


def _num_to_words_en(n: int) -> str:
    return num2words(n, lang="en").replace("-", " ")


def expand_numbers_en(text: str) -> str:
    """Expands numbers in English text: 1 → one, #1 → number one."""
    def repl_hash(m: re.Match) -> str:
        n = int(m.group(1))
        return f"number {_num_to_words_en(n)}"

    text = HASH_NUM_RE.sub(repl_hash, text)

    def repl_standalone_en(m: re.Match) -> str:
        n = int(m.group(1))
        return _num_to_words_en(n)

    text = STANDALONE_INT_RE.sub(repl_standalone_en, text)
    return text

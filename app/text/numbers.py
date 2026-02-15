import re
from num2words import num2words
from app.text.morph import agree_word_with_number, match_case

NUM_NOUN_RE = re.compile(r"(?<!\w)(\d{1,18})\s+([А-Яа-яЁё]+)(?!\w)")
PERCENT_RE = re.compile(r"(?<!\w)(\d{1,18})\s*%(?!\w)")
RUBLE_RE = re.compile(r"(?<!\w)(\d{1,18})\s*(₽|руб\.?|рубля|рублей|рубль)(?!\w)", re.IGNORECASE)
STANDALONE_INT_RE = re.compile(r"(?<!\d\.)\b(\d{1,18})\b(?![.:]\d)")

def _num_to_words_ru(n: int) -> str:
    return num2words(n, lang="ru").replace("-", " ")

def expand_numbers(text: str) -> str:
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

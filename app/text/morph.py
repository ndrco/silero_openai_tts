import pymorphy3

_morph = pymorphy3.MorphAnalyzer(lang="ru")

def _best_noun_parse(word: str):
    parses = _morph.parse(word)
    for p in parses:
        if p.tag.POS == "NOUN":
            return p
    return parses[0] if parses else None

def agree_word_with_number(word: str, n: int) -> str:
    p = _best_noun_parse(word)
    if p is None:
        return word
    agreed = p.make_agree_with_number(n)
    return agreed.word if agreed else word

def match_case(template: str, word: str) -> str:
    if template.isupper():
        return word.upper()
    if template.istitle():
        return word[:1].upper() + word[1:]
    return word

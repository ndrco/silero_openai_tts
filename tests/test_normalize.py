"""Tests for text normalization (URL → "link", EN numbers, etc.)."""
from app.text.normalize import TextNormalizer, clean_markdown_for_tts, replace_urls, strip_unsupported_symbols
from app.text.numbers import expand_numbers_en


def test_replace_urls_http():
    assert "link" in replace_urls("Заходи на http://example.com сюда")
    assert replace_urls("http://foo.bar/baz") == " link "


def test_replace_urls_https():
    assert "link" in replace_urls("https://github.com")


def test_normalizer_does_not_replace_url():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=False)
    out = n.run("Текст с https://link.ru внутри.")
    assert "https://link.ru" in out


def test_label_kept_url_replaced():
    """The label (GitHub:) remains; only the URL is replaced with "link"."""
    out = replace_urls("Ссылка на GitHub: https://github.com/ndrco/silero_openai_tts")
    assert "Ссылка на GitHub:" in out
    assert "link" in out
    assert "GitHub" in out
    assert "github.com" not in out


def test_expand_numbers_en():
    assert expand_numbers_en("long audio #1.") == "long audio number one."
    assert "two" in expand_numbers_en("We have 2 goals.")


def test_strip_unsupported_symbols_removes_caret_for_ru():
    assert strip_unsupported_symbols("Мой тест ^ 732", lang="ru") == "Мой тест   732"


def test_strip_unsupported_symbols_removes_technical_ru_symbols():
    out = strip_unsupported_symbols("curl wttr.in/Moscow?format=%l:+%t+%w", lang="ru")
    assert "/" not in out
    assert "%" not in out
    assert ":" not in out
    assert "+" not in out


def test_normalizer_removes_unsupported_symbols_for_ru():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=False, expand_numeric_lang="ru")
    out = n.run("Мой тест ^ 732")
    assert "^" not in out
    assert out == "Мой тест 732"


def test_normalizer_expands_time_for_ru():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=True, expand_numeric_lang="ru")
    out = n.run("Сейчас 14:06")
    assert out == "Сейчас четырнадцать часов шесть минут"


def test_normalizer_expands_utc_offset_with_plus():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=True, expand_numeric_lang="ru")
    out = n.run("GMT+3 / Москва")
    assert out == "GMT плюс три слэш Москва"


def test_normalizer_expands_signed_numbers_and_range():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=True, expand_numeric_lang="ru")
    out = n.run("Температура -5, диапазон 10-15")
    assert out == "Температура минус пять, диапазон от десять до пятнадцать"


def test_normalizer_expands_decimal_numbers_for_ru():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=True, expand_numeric_lang="ru")
    out = n.run("Число 3.14")
    assert out == "Число три целых четырнадцать сотых"


def test_normalizer_keeps_technical_patterns_untouched():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=True, expand_numeric_lang="ru")
    out = n.run("Версия v1.2.3, IP 192.168.0.1, дата 01.02.2025")
    assert out == "Версия v1.2.3, IP 192.168.0.1, дата 01.02.2025"


def test_clean_markdown_for_tts_removes_code_and_placeholders():
    text = (
        "Базовое использование:\n"
        "```bash\n"
        "curl wttr.in/Moscow?format=%l:+%t+%w\n"
        "```\n"
        "См. `curl wttr.in` и [документацию](https://wttr.in/:help)."
    )
    out = clean_markdown_for_tts(text)
    assert "```" not in out
    assert "`" not in out
    assert "%l" not in out
    assert "?format=" not in out
    assert "документацию" in out


def test_normalizer_verbalizes_technical_symbols_for_ru():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=False, expand_numeric_lang="ru")
    out = n.run("Путь /, процент %, плюс +, равно =, двоеточие :")
    assert "слэш" in out
    assert "процент" in out
    assert "плюс" in out
    assert "равно" in out
    assert "двоеточие" in out

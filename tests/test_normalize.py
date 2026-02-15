"""Tests for text normalization (URL → "link", EN numbers, etc.)."""
from app.text.normalize import TextNormalizer, replace_urls
from app.text.numbers import expand_numbers_en


def test_replace_urls_http():
    assert "ссылка" in replace_urls("Заходи на http://example.com сюда")
    assert replace_urls("http://foo.bar/baz") == " ссылка "


def test_replace_urls_https():
    assert "ссылка" in replace_urls("https://github.com")


def test_normalizer_replaces_url():
    n = TextNormalizer(transliterate_latin=False, expand_numeric=False)
    out = n.run("Текст с https://link.ru внутри.")
    assert "ссылка" in out
    assert "https://" not in out


def test_label_kept_url_replaced():
    """The label (GitHub:) remains; only the URL is replaced with "link"."""
    n = TextNormalizer(transliterate_latin=False, expand_numeric=False)
    out = n.run("Ссылка на GitHub: https://github.com/ndrco/silero_openai_tts")
    assert out == "Ссылка на GitHub: ссылка"
    assert "GitHub" in out
    assert "github.com" not in out


def test_expand_numbers_en():
    assert expand_numbers_en("long audio #1.") == "long audio number one."
    assert "two" in expand_numbers_en("We have 2 goals.")

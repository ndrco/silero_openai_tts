from app.text.language_router import LanguageAwareRouter


def test_detect_ru_en_and_mixed() -> None:
    router = LanguageAwareRouter()
    assert router.detect("Привет мир") == "ru"
    assert router.detect("hello world") == "en"
    assert router.detect("Привет hello") == "mixed"


def test_split_mixed_text_preserves_order() -> None:
    router = LanguageAwareRouter()
    segments = router.split("Привет, hello world! Как дела?")
    assert [(s.lang, s.text) for s in segments] == [
        ("ru", "Привет,"),
        ("en", "hello world!"),
        ("ru", "Как дела?"),
    ]

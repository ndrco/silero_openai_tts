"""Tests for Latin-to-Cyrillic transliteration."""
import pytest
from app.text.transliterate import transliterate_latin_to_cyrillic


def test_hello():
    assert "хелло" in transliterate_latin_to_cyrillic("hello")


def test_api():
    assert transliterate_latin_to_cyrillic("API") == "АПИ"


def test_mixed_unchanged():
    s = "Слово hello и ещё слово."
    out = transliterate_latin_to_cyrillic(s)
    assert "Слово" in out and "слово" in out
    assert "хелло" in out


def test_cyrillic_only_unchanged():
    assert transliterate_latin_to_cyrillic("Только кириллица.") == "Только кириллица."

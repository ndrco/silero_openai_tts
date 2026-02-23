from app.text.ssml import inject_medium_breaks_for_newlines, split_by_medium_break


def test_inject_medium_breaks_for_newlines() -> None:
    text = "Первая строка\nВторая строка\r\nТретья"
    out = inject_medium_breaks_for_newlines(text)
    assert '<break strength="medium"/>' in out
    assert out.count('<break strength="medium"/>') == 2


def test_split_by_medium_break() -> None:
    text = 'A <break strength="medium"/> B <break strength="medium"/> C'
    parts = split_by_medium_break(text)
    assert parts == ["A ", " B ", " C"]

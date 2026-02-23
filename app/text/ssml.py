import re

MEDIUM_BREAK_TAG = '<break strength="medium"/>'
_NEWLINE_RE = re.compile(r"\r?\n")
_MEDIUM_BREAK_RE = re.compile(r"<break\s+strength\s*=\s*['\"]medium['\"]\s*/>", re.IGNORECASE)


def inject_medium_breaks_for_newlines(text: str) -> str:
    """Converts every newline into SSML medium break tag."""
    return _NEWLINE_RE.sub(f" {MEDIUM_BREAK_TAG} ", text or "")


def split_by_medium_break(text: str) -> list[str]:
    """Splits text into fragments by SSML medium breaks, preserving empty fragments."""
    return _MEDIUM_BREAK_RE.split(text or "")

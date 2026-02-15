from app.text.numbers import expand_numbers

class TextNormalizer:
    def run(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        t = expand_numbers(t)
        t = " ".join(t.split())
        return t

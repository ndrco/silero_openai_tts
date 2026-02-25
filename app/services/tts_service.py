import logging

from app.audio.concat import concat_wav_bytes
from app.text.normalize import clean_markdown_for_tts, replace_urls, strip_unsupported_symbols, verbalize_technical_symbols_ru
from app.text.ssml import inject_medium_breaks_for_newlines, split_by_medium_break


class TTSService:
    """Orchestrates text normalization/routing and synthesis across one or two engines."""

    def __init__(
        self,
        *,
        settings,
        ru_engine,
        ru_normalizer,
        en_engine=None,
        en_normalizer=None,
        language_router=None,
        log: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.ru_engine = ru_engine
        self.ru_normalizer = ru_normalizer
        self.en_engine = en_engine
        self.en_normalizer = en_normalizer
        self.language_router = language_router
        self.log = log or logging.getLogger("silero")

    def synthesize(self, text: str, speaker: str) -> bytes:
        return self._synthesize_with_newline_ssml_breaks(text, speaker)

    def _synthesize_ru_with_fallback(self, text: str, speaker: str, *, reject_log_prefix: str) -> bytes:
        """Synthesizes RU text with two-stage fallback to avoid 500 on parser rejects."""
        normalized = self.ru_normalizer.run(text)
        normalized = normalized if normalized.strip() else " "
        try:
            return self.ru_engine.synthesize_wav_bytes(normalized, speaker=speaker)
        except (ValueError, RuntimeError, KeyError) as e:
            self.log.warning("%s, sanitizing fallback: %s", reject_log_prefix, e)

        safe_text = verbalize_technical_symbols_ru(normalized)
        safe_text = strip_unsupported_symbols(safe_text, lang="ru")
        safe_text = " ".join(safe_text.split()) or " "

        try:
            return self.ru_engine.synthesize_wav_bytes(safe_text, speaker=speaker)
        except (ValueError, RuntimeError, KeyError) as e:
            self.log.warning("%s, second fallback failed: %s", reject_log_prefix, e)

        neutral_text = "Текст недоступен"
        try:
            return self.ru_engine.synthesize_wav_bytes(neutral_text, speaker=speaker)
        except (ValueError, RuntimeError, KeyError) as e:
            self.log.warning("%s, neutral fallback failed, returning silence: %s", reject_log_prefix, e)
            return self.ru_engine.synthesize_wav_bytes(" ", speaker=speaker)

    def _synthesize_with_routing(self, text: str, speaker: str) -> bytes:
        # Replace URL before language split so "Link to GitHub: https://..." keeps a coherent segment.
        routed_text = replace_urls(clean_markdown_for_tts(text))
        segments = self.language_router.split(routed_text)
        if not segments:
            return self.ru_engine.synthesize_wav_bytes(" ", speaker=speaker)

        wav_parts = []
        for segment in segments:
            if segment.lang == "en" and self.en_engine is not None:
                normalized = self.en_normalizer.run(segment.text)
                if not normalized or not normalized.strip():
                    normalized = " "
                try:
                    wav_parts.append(
                        self.en_engine.synthesize_wav_bytes(normalized, speaker=self.en_engine.default_speaker)
                    )
                except (ValueError, RuntimeError) as e:
                    self.log.warning("EN model rejected segment, fallback to RU: %s", e)
                    normalized_ru = self.ru_normalizer.run(segment.text)
                    wav_parts.append(self.ru_engine.synthesize_wav_bytes(normalized_ru, speaker=speaker))
            else:
                wav_parts.append(
                    self._synthesize_ru_with_fallback(segment.text, speaker, reject_log_prefix="RU model rejected segment")
                )

        pause_sec = self.settings.silero_pause_between_fragments_sec
        return concat_wav_bytes(wav_parts, expected_sample_rate=self.ru_engine.sample_rate, pause_sec=pause_sec)

    def _synthesize_with_newline_ssml_breaks(self, text: str, speaker: str) -> bytes:
        """Converts '\n' to SSML medium breaks and applies pauses between synthesized fragments."""
        cleaned_text = clean_markdown_for_tts(text)
        ssml_text = inject_medium_breaks_for_newlines(cleaned_text)
        fragments = split_by_medium_break(ssml_text)

        wav_parts = []
        for fragment in fragments:
            if not fragment.strip():
                continue
            if self.settings.language_aware_routing:
                wav_parts.append(self._synthesize_with_routing(fragment, speaker))
            else:
                wav_parts.append(
                    self._synthesize_ru_with_fallback(fragment, speaker, reject_log_prefix="RU model rejected fragment")
                )

        if not wav_parts:
            wav_parts = [self.ru_engine.synthesize_wav_bytes(" ", speaker=speaker)]

        return concat_wav_bytes(
            wav_parts,
            expected_sample_rate=self.ru_engine.sample_rate,
            pause_sec=self.settings.silero_pause_between_fragments_sec,
        )

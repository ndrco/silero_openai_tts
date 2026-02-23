import logging

from app.audio.concat import concat_wav_bytes
from app.text.normalize import replace_urls, strip_unsupported_symbols
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

    def _synthesize_with_routing(self, text: str, speaker: str) -> bytes:
        # Replace URL before language split so "Link to GitHub: https://..." keeps a coherent segment.
        routed_text = replace_urls(text)
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
                normalized = self.ru_normalizer.run(segment.text)
                if not normalized or not normalized.strip():
                    normalized = " "
                try:
                    wav_parts.append(self.ru_engine.synthesize_wav_bytes(normalized, speaker=speaker))
                except (ValueError, RuntimeError, KeyError) as e:
                    self.log.warning("RU model rejected segment, sanitizing fallback: %s", e)
                    safe_text = strip_unsupported_symbols(normalized, lang="ru")
                    safe_text = " ".join(safe_text.split()) or " "
                    wav_parts.append(self.ru_engine.synthesize_wav_bytes(safe_text, speaker=speaker))

        pause_sec = self.settings.silero_pause_between_fragments_sec
        return concat_wav_bytes(wav_parts, expected_sample_rate=self.ru_engine.sample_rate, pause_sec=pause_sec)

    def _synthesize_with_newline_ssml_breaks(self, text: str, speaker: str) -> bytes:
        """Converts '\n' to SSML medium breaks and applies pauses between synthesized fragments."""
        ssml_text = inject_medium_breaks_for_newlines(text)
        fragments = split_by_medium_break(ssml_text)

        wav_parts = []
        for fragment in fragments:
            if not fragment.strip():
                continue
            if self.settings.language_aware_routing:
                wav_parts.append(self._synthesize_with_routing(fragment, speaker))
            else:
                normalized = self.ru_normalizer.run(fragment)
                normalized = normalized if normalized.strip() else " "
                try:
                    wav_parts.append(self.ru_engine.synthesize_wav_bytes(normalized, speaker=speaker))
                except (ValueError, RuntimeError, KeyError) as e:
                    self.log.warning("RU model rejected fragment, sanitizing fallback: %s", e)
                    safe_text = strip_unsupported_symbols(normalized, lang="ru")
                    safe_text = " ".join(safe_text.split()) or " "
                    wav_parts.append(self.ru_engine.synthesize_wav_bytes(safe_text, speaker=speaker))

        if not wav_parts:
            wav_parts = [self.ru_engine.synthesize_wav_bytes(" ", speaker=speaker)]

        return concat_wav_bytes(
            wav_parts,
            expected_sample_rate=self.ru_engine.sample_rate,
            pause_sec=self.settings.silero_pause_between_fragments_sec,
        )

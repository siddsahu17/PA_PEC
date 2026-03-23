import subprocess
import logging

logger = logging.getLogger("assistant_backend.braille")

class BrailleService:
    @staticmethod
    def _translate_with_liblouis(text: str) -> str:
        """
        Calls `lou_translate` which is part of liblouis-bin.
        Uses en-us-g2.ctb for English Grade 2 braille translation.
        """
        try:
            process = subprocess.run(
                ["lou_translate", "en-us-g2.ctb"],
                input=text.encode("utf-8"),
                capture_output=True,
                check=True
            )
            return process.stdout.decode("utf-8").strip()
        except FileNotFoundError:
            logger.warning("lou_translate not found. Is liblouis-bin installed? Using fallback mock translation.")
            return BrailleService._fallback_mock(text)
        except Exception as e:
            logger.error(f"Error executing lou_translate: {e}")
            return BrailleService._fallback_mock(text)

    @staticmethod
    def _fallback_mock(text: str) -> str:
        # A simple fallback mock if liblouis isn't available
        # Replace normal characters with a mock dot representation for demonstration
        char_map = {
            'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑', 'f': '⠋', 'g': '⠛',
            'h': '⠓', 'i': '⠊', 'j': '⠚', 'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝',
            'o': '⠕', 'p': '⠏', 'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞', 'u': '⠥',
            'v': '⠧', 'w': '⠺', 'x': '⠭', 'y': '⠽', 'z': '⠵', ' ': ' ',
        }
        return "".join([char_map.get(c.lower(), '⠂') for c in text])

    @staticmethod
    def translate(text: str) -> str:
        return BrailleService._translate_with_liblouis(text)

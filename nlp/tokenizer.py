# Copyright (c) 2026 Karunakar (destroyer929). All rights reserved.
# Proprietary & Confidential. Authorized for technical evaluation and portfolio review only.
"""
Japanese Architectural Morphological Tokenizer.
Integrates SudachiPy to segment spaceless Japanese text into architectural morphemes,
compound nouns, and key construction terms.
Enables token-aware fuzzy matching and character n-gram extraction.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import threading
from dataclasses import dataclass
from sudachipy import dictionary, tokenizer


@dataclass
class MorphemeToken:
    """Represents a segmented Japanese morpheme with part-of-speech."""
    surface: str
    normalized_form: str
    dictionary_form: str
    part_of_speech: List[str]
    is_content_word: bool


class JapaneseMorphologicalTokenizer:
    """Tokenizes continuous Japanese architectural text into morphemes using SudachiPy."""

    def __init__(self, split_mode: str = "B"):
        # SudachiPy split modes:
        # A: Short unit (morpheme level)
        # B: Medium unit (compound words) - ideal for architectural terms
        # C: Long unit (named entity level)
        self.dict = dictionary.Dictionary()
        self._lock = threading.Lock()
        if hasattr(self.dict, "tokenizer"):
            self.tokenizer = self.dict.tokenizer()
        else:
            self.tokenizer = self.dict.create()
        if split_mode == "A":
            self.mode = tokenizer.Tokenizer.SplitMode.A
        elif split_mode == "C":
            self.mode = tokenizer.Tokenizer.SplitMode.C
        else:
            self.mode = tokenizer.Tokenizer.SplitMode.B

    def tokenize(self, text: str) -> List[MorphemeToken]:
        """Segments text into detailed morpheme tokens."""
        if not text:
            return []

        with self._lock:
            morphemes = self.tokenizer.tokenize(text, self.mode)
        tokens: List[MorphemeToken] = []

        for m in morphemes:
            pos = list(m.part_of_speech())
            pos_major = pos[0] if pos else ""

            # Content words: Nouns (名詞), Verbs (動詞), Adjectives (形容詞)
            # Exclude particles (助詞), auxiliary verbs (助動詞), and punctuation (補助記号)
            is_content = pos_major in ("名詞", "動詞", "形容詞") and pos[1] not in ("非自立", "接尾")

            tokens.append(
                MorphemeToken(
                    surface=m.surface(),
                    normalized_form=m.normalized_form(),
                    dictionary_form=m.dictionary_form(),
                    part_of_speech=pos,
                    is_content_word=is_content
                )
            )

        return tokens

    def get_content_words(self, text: str) -> List[str]:
        """Returns only the core semantic content words (e.g. ['吹付け', 'ロックウール'])."""
        tokens = self.tokenize(text)
        return [t.normalized_form for t in tokens if t.is_content_word and len(t.surface.strip()) > 0]

    def to_spaced_string(self, text: str) -> str:
        """Converts continuous Japanese text into a space-delimited string for token matching."""
        tokens = self.tokenize(text)
        return " ".join(t.surface for t in tokens if t.surface.strip())

    @staticmethod
    def get_character_ngrams(text: str, n: int = 2) -> List[str]:
        """Extracts character n-grams for radical and character-level similarity."""
        cleaned = "".join(text.split())
        if len(cleaned) < n:
            return [cleaned] if cleaned else []
        return [cleaned[i : i + n] for i in range(len(cleaned) - n + 1)]


if __name__ == "__main__":
    tok = JapaneseMorphologicalTokenizer(split_mode="B")
    sample_text = "鉄骨梁: 吹付けロックウール t=25 (耐火被覆)"
    tokens = tok.tokenize(sample_text)
    print("SudachiPy Morphemes:")
    for t in tokens:
        print(f"  {t.surface:12s} POS: {t.part_of_speech[:2]} (Content: {t.is_content_word})")

    print("\nContent Words:", tok.get_content_words(sample_text))
    print("Spaced String:", tok.to_spaced_string(sample_text))
    print("Character Bigrams:", tok.get_character_ngrams("ロックウール", n=2))

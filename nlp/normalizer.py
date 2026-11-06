"""
Text Normalization Pipeline for Architectural Annotations.
Performs Unicode NFKC normalization, converts full-width Japanese alphanumerics
to half-width, standardizes thickness and dimension patterns, and cleans OCR punctuation noise
while preserving the original string for regulatory auditability.
"""

from __future__ import annotations
import unicodedata
import re
from typing import Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class NormalizedText:
    """Holds both original and normalized text representations for review transparency."""
    original_text: str
    cleaned_text: str
    thickness_spec: str = ""
    is_modified: bool = False


class TextNormalizer:
    """Normalizes raw OCR transcriptions into canonical architectural tokens."""

    # Punctuation to clean from raw OCR text
    PUNCT_CLEANUP = re.compile(r"[\s\t\r\n\|_~`=\*\[\]{}<>]+", re.UNICODE)

    # Thickness patterns: t=25, 25mm, 厚25, 25㎜
    THICKNESS_PATTERNS = [
        re.compile(r"t\s*=\s*(\d+(\.\d+)?)", re.IGNORECASE),
        re.compile(r"(\d+(\.\d+)?)\s*(?:mm|㎜)", re.IGNORECASE),
        re.compile(r"厚\s*(\d+(\.\d+)?)")
    ]

    def normalize(self, raw_text: str) -> NormalizedText:
        """Applies full normalization pipeline to raw OCR text."""
        if not raw_text:
            return NormalizedText("", "", "", False)

        original = raw_text.strip()

        # 1. Unicode NFKC normalization:
        # Full-width '２５ｍｍ' -> '25mm'
        # Full-width '（' -> '('
        # Half-width kana -> Full-width standard kana
        nfkc = unicodedata.normalize("NFKC", original)

        # 2. Extract and preserve thickness specification
        thickness = ""
        for pat in self.THICKNESS_PATTERNS:
            m = pat.search(nfkc)
            if m:
                val = m.group(1)
                thickness = f"t={val}"
                break

        # 3. Clean OCR noise and standardize spacing
        # Replace multiple spaces or tabs
        cleaned = re.sub(r"\s+", " ", nfkc).strip()

        # Remove surrounding punctuation artifacts like leading quotes, colons, or dashes
        cleaned = re.sub(r"^[\s:;,\-\.\'\"（(【\[]+", "", cleaned)
        cleaned = re.sub(r"[\s:;,\-\.\'\"）)】\]]+$", "", cleaned)

        is_mod = (cleaned != original)

        return NormalizedText(
            original_text=original,
            cleaned_text=cleaned,
            thickness_spec=thickness,
            is_modified=is_mod
        )


if __name__ == "__main__":
    normalizer = TextNormalizer()
    samples = [
        "２５ｍｍ",
        "  鉄骨梁: 吹付けロックウール ｔ＝２５  (耐火被覆) ",
        "［けい酸カルシウム板第１種　ｔ＝８］",
        "ビニル床タイル　３００ｘ３００",
        "スレート波板　厚6.3"
    ]
    print("Testing Text Normalizer:")
    for s in samples:
        res = normalizer.normalize(s)
        print(f"  Raw: '{res.original_text}' -> Cleaned: '{res.cleaned_text}' (Thickness: {res.thickness_spec})")


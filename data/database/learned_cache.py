"""
Persistent Learned Material Cache for Japanese Architectural Asbestos Detection.
Caches definitive LLM classifications (POSITIVE / NEGATIVE) permanently to disk.
On subsequent scans of other blueprints, queries hitting the learned cache resolve
instantly in Tier 1 (< 1ms) without calling the local LLM.
Strictly excludes UNCERTAIN classifications.
"""

from __future__ import annotations
import os
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("alfred.learned_cache")


class LearnedRecord(BaseModel):
    query_text: str
    status: str  # POSITIVE or NEGATIVE (never UNCERTAIN)
    hazard_level: str  # LEVEL_1, LEVEL_2, LEVEL_3, NON_ASBESTOS
    matched_material_ja: str
    matched_material_en: str
    confidence: float
    regulatory_citation: str
    source: str = "TIER_5_LLM_ARBITRATION"
    learned_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LearnedMaterialCache:
    """
    Thread-safe persistent cache for LLM-arbitrated building materials.
    Stores results in JSON format on disk.
    """

    DEFAULT_CACHE_FILE = Path(__file__).parent / "learned_materials.json"

    def __init__(self, cache_file: Optional[Path | str] = None):
        self.cache_file = Path(cache_file) if cache_file else self.DEFAULT_CACHE_FILE
        self._lock = threading.RLock()
        self._cache: Dict[str, LearnedRecord] = {}
        self.load()

    def _normalize_key(self, text: str) -> str:
        """Normalizes lookup key for consistent cache retrieval."""
        if not text:
            return ""
        return text.strip().lower()

    def load(self) -> None:
        """Loads learned materials from disk into memory."""
        with self._lock:
            self._cache.clear()
            if not self.cache_file.exists():
                return

            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                records = data if isinstance(data, list) else data.get("records", [])
                for item in records:
                    try:
                        record = LearnedRecord(**item)
                        key = self._normalize_key(record.query_text)
                        if key:
                            self._cache[key] = record
                    except Exception as parse_err:
                        logger.warning(f"Skipping malformed learned cache entry: {parse_err}")

                logger.info(f"Loaded {len(self._cache)} learned material records from {self.cache_file.name}")
            except Exception as e:
                logger.error(f"Failed to load learned material cache: {e}")

    def save(self) -> None:
        """Atomically persists in-memory cache to disk."""
        with self._lock:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                records_list = [r.model_dump() for r in self._cache.values()]
                payload = {
                    "version": "1.0",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "total_records": len(records_list),
                    "records": records_list
                }

                temp_file = self.cache_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                # Atomic replacement
                if os.name == "nt" and self.cache_file.exists():
                    os.replace(temp_file, self.cache_file)
                else:
                    temp_file.replace(self.cache_file)

            except Exception as e:
                logger.error(f"Failed to save learned material cache to {self.cache_file}: {e}")

    def lookup(self, query: str) -> Optional[LearnedRecord]:
        """Checks if a normalized query has been previously classified."""
        key = self._normalize_key(query)
        if not key:
            return None
        with self._lock:
            return self._cache.get(key)

    def record_decision(
        self,
        query_text: str,
        status: str,
        hazard_level: str,
        matched_material_ja: str,
        matched_material_en: str,
        confidence: float,
        reasoning: str,
        persist: bool = True
    ) -> bool:
        """
        Records a newly arbitrated classification.
        CRITICAL RULE: Only records POSITIVE or NEGATIVE determinations.
        Never saves UNCERTAIN items.
        """
        clean_status = str(status).strip().upper()
        if clean_status not in ("POSITIVE", "NEGATIVE"):
            logger.debug(f"Skipping learned cache for '{query_text}': status '{clean_status}' is not POSITIVE or NEGATIVE.")
            return False

        if confidence < 0.75:
            logger.debug(f"Skipping learned cache for '{query_text}': confidence {confidence:.2f} < 0.75.")
            return False

        key = self._normalize_key(query_text)
        if not key:
            return False

        record = LearnedRecord(
            query_text=query_text.strip(),
            status=clean_status,
            hazard_level=hazard_level.strip().upper(),
            matched_material_ja=matched_material_ja.strip(),
            matched_material_en=matched_material_en.strip(),
            confidence=float(confidence),
            regulatory_citation=f"Learned LLM Arbitration: {reasoning.strip()}",
            source="TIER_5_LLM_ARBITRATION"
        )

        with self._lock:
            self._cache[key] = record
            if persist:
                self.save()

        logger.info(f"Learned material cached: '{query_text}' -> {clean_status} ({hazard_level}, conf={confidence:.2f})")
        return True

    def get_all(self) -> Dict[str, LearnedRecord]:
        with self._lock:
            return dict(self._cache)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

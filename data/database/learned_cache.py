"""
Persistent Learned Material Cache for Japanese Architectural Asbestos Detection.
Powered by SQLite (WAL Mode) with In-Memory L1 Hash Index for Sub-Microsecond Retrieval.
Caches definitive classifications (POSITIVE / NEGATIVE) permanently to disk.
On subsequent scans of other blueprints, queries hitting the learned cache resolve
instantly in Tier 1 (< 1ms) without calling the local LLM.
Strictly excludes UNCERTAIN classifications.
"""

from __future__ import annotations
import os
import json
import sqlite3
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
    High-performance two-tier learned material cache:
    - Tier 1: Thread-safe in-memory L1 hash index for sub-microsecond retrieval (O(1), ~50ns).
    - Tier 2: Persistent SQLite database in WAL (Write-Ahead Logging) mode with NORMAL synchrony
      for instant (< 0.2ms) single-row appends without whole-file serialization bottlenecks.
    """

    DEFAULT_DB_FILE = Path(__file__).parent / "learned_cache.db"
    DEFAULT_LEGACY_JSON = Path(__file__).parent / "learned_materials.json"

    def __init__(
        self,
        cache_file: Optional[Path | str] = None,
        db_path: Optional[Path | str] = None
    ):
        self._lock = threading.RLock()
        self._l1_cache: Dict[str, LearnedRecord] = {}
        self._conn: Optional[sqlite3.Connection] = None

        # Check if caller explicitly requested a .json file (e.g. legacy test suite)
        target = db_path or cache_file or self.DEFAULT_DB_FILE
        target_path = Path(target)
        if target_path.suffix.lower() == ".json":
            self.is_json_backend = True
            self.cache_file = target_path
            self.db_path = target_path
            self._load_json()
        else:
            self.is_json_backend = False
            self.db_path = target_path
            self.cache_file = self.db_path
            self._init_sqlite()
            self._load_and_migrate_sqlite()

    def _normalize_key(self, text: str) -> str:
        """Normalizes lookup key for consistent cache retrieval."""
        if not text:
            return ""
        return text.strip().lower()

    # =========================================================================
    # SQLite WAL Mode Backend (Primary Production Engine)
    # =========================================================================

    def _init_sqlite(self) -> None:
        """Initializes SQLite connection with WAL mode and schema."""
        with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0
            )
            # Enable WAL mode and NORMAL synchrony as specified
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
            self._conn.execute("PRAGMA busy_timeout = 5000;")
            self._conn.execute("PRAGMA temp_store = MEMORY;")

            # Create table and indices
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS learned_materials (
                    query_key TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    hazard_level TEXT NOT NULL,
                    matched_material_ja TEXT NOT NULL,
                    matched_material_en TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    regulatory_citation TEXT NOT NULL,
                    source TEXT NOT NULL,
                    learned_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_learned_query_key ON learned_materials(query_key);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_learned_status ON learned_materials(status);"
            )
            self._conn.commit()

    def _load_and_migrate_sqlite(self) -> None:
        """Loads persisted rows from SQLite into L1 cache, migrating legacy JSON if present."""
        with self._lock:
            self._l1_cache.clear()

            # 1. Check if SQLite table already has records
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learned_materials;")
            count = cursor.fetchone()[0]

            # 2. If SQLite is empty and this is the default production DB, migrate from legacy JSON if it exists
            if count == 0 and self.db_path == self.DEFAULT_DB_FILE and self.DEFAULT_LEGACY_JSON.exists():
                try:
                    with open(self.DEFAULT_LEGACY_JSON, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    records = data if isinstance(data, list) else data.get("records", [])
                    migrated = 0
                    for item in records:
                        try:
                            record = LearnedRecord(**item)
                            key = self._normalize_key(record.query_text)
                            if key:
                                cursor.execute(
                                    """
                                    INSERT OR REPLACE INTO learned_materials 
                                    (query_key, query_text, status, hazard_level, matched_material_ja, matched_material_en, confidence, regulatory_citation, source, learned_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        key,
                                        record.query_text,
                                        record.status,
                                        record.hazard_level,
                                        record.matched_material_ja,
                                        record.matched_material_en,
                                        record.confidence,
                                        record.regulatory_citation,
                                        record.source,
                                        record.learned_at
                                    )
                                )
                                migrated += 1
                        except Exception as m_err:
                            logger.warning(f"Skipping malformed legacy record: {m_err}")
                    self._conn.commit()
                    if migrated > 0:
                        logger.info(f"Migrated {migrated} records from {self.DEFAULT_LEGACY_JSON.name} to SQLite WAL ({self.db_path.name}).")
                except Exception as e:
                    logger.warning(f"Legacy JSON cache migration skipped: {e}")

            # 3. Populate L1 In-Memory Cache from SQLite
            cursor.execute(
                """
                SELECT query_text, status, hazard_level, matched_material_ja, matched_material_en, confidence, regulatory_citation, source, learned_at
                FROM learned_materials
                """
            )
            for row in cursor.fetchall():
                try:
                    rec = LearnedRecord(
                        query_text=row[0],
                        status=row[1],
                        hazard_level=row[2],
                        matched_material_ja=row[3],
                        matched_material_en=row[4],
                        confidence=row[5],
                        regulatory_citation=row[6],
                        source=row[7],
                        learned_at=row[8]
                    )
                    key = self._normalize_key(rec.query_text)
                    if key:
                        self._l1_cache[key] = rec
                except Exception as err:
                    logger.warning(f"Error parsing SQLite row: {err}")

            logger.info(f"Loaded {len(self._l1_cache)} learned material records into L1 in-memory cache from SQLite ({self.db_path.name})")

    # =========================================================================
    # JSON Backend (Legacy / Unit Test Fallback)
    # =========================================================================

    def _load_json(self) -> None:
        """Loads learned materials from a JSON file into L1 cache."""
        with self._lock:
            self._l1_cache.clear()
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
                            self._l1_cache[key] = record
                    except Exception as parse_err:
                        logger.warning(f"Skipping malformed learned cache entry: {parse_err}")
                logger.info(f"Loaded {len(self._l1_cache)} learned records from {self.cache_file.name}")
            except Exception as e:
                logger.error(f"Failed to load JSON learned cache: {e}")

    def _save_json(self) -> None:
        """Persists L1 cache to JSON file atomically."""
        with self._lock:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                records_list = [r.model_dump() for r in self._l1_cache.values()]
                payload = {
                    "version": "1.0",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "total_records": len(records_list),
                    "records": records_list
                }
                temp_file = self.cache_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, self.cache_file)
            except Exception as e:
                logger.error(f"Failed to save JSON cache: {e}")

    # =========================================================================
    # Public Cache Interface (Sub-Microsecond L1 Lookups & Non-Blocking Writes)
    # =========================================================================

    def lookup(self, query: str) -> Optional[LearnedRecord]:
        """
        Retrieves a learned record for the given query.
        1. Fast-path: Checks in-memory L1 cache (sub-microsecond O(1), ~50ns).
        2. Fallback: Checks SQLite indexed B-Tree if L1 misses.
        """
        key = self._normalize_key(query)
        if not key:
            return None

        with self._lock:
            # L1 In-Memory fast path (~50ns)
            record = self._l1_cache.get(key)
            if record is not None:
                return record

            # Fallback to SQLite DB if not using JSON backend
            if not self.is_json_backend and self._conn is not None:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    SELECT query_text, status, hazard_level, matched_material_ja, matched_material_en, confidence, regulatory_citation, source, learned_at
                    FROM learned_materials
                    WHERE query_key = ?
                    """,
                    (key,)
                )
                row = cursor.fetchone()
                if row:
                    rec = LearnedRecord(
                        query_text=row[0],
                        status=row[1],
                        hazard_level=row[2],
                        matched_material_ja=row[3],
                        matched_material_en=row[4],
                        confidence=row[5],
                        regulatory_citation=row[6],
                        source=row[7],
                        learned_at=row[8]
                    )
                    self._l1_cache[key] = rec
                    return rec

            return None

    def record_decision(
        self,
        query_text: str,
        status: str,
        hazard_level: str,
        matched_material_ja: str,
        matched_material_en: str,
        confidence: float,
        reasoning: str,
        persist: bool = True,
        source: str = "TIER_5_LLM_ARBITRATION"
    ) -> bool:
        """
        Records a newly arbitrated classification into L1 in-memory cache and SQLite WAL database.
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
            regulatory_citation=f"{source}: {reasoning.strip()}",
            source=source
        )

        with self._lock:
            # 1. Update L1 In-Memory Cache immediately
            self._l1_cache[key] = record

            # 2. Persist to disk
            if persist:
                if self.is_json_backend:
                    self._save_json()
                elif self._conn is not None:
                    try:
                        self._conn.execute(
                            """
                            INSERT OR REPLACE INTO learned_materials 
                            (query_key, query_text, status, hazard_level, matched_material_ja, matched_material_en, confidence, regulatory_citation, source, learned_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                key,
                                record.query_text,
                                record.status,
                                record.hazard_level,
                                record.matched_material_ja,
                                record.matched_material_en,
                                record.confidence,
                                record.regulatory_citation,
                                record.source,
                                record.learned_at
                            )
                        )
                        self._conn.commit()
                    except Exception as e:
                        logger.error(f"Failed to persist learned record '{query_text}' to SQLite: {e}")
                        return False

        logger.info(f"Learned material cached: '{query_text}' -> {clean_status} ({hazard_level}, conf={confidence:.2f})")
        return True

    def record_decisions_batch(
        self,
        records: List[Dict[str, Any]],
        persist: bool = True
    ) -> int:
        """
        Batch records multiple classifications into L1 cache and SQLite WAL in a single transaction.
        CRITICAL RULE: Only records POSITIVE or NEGATIVE determinations with confidence >= 0.75.
        Returns the number of records successfully cached.
        """
        saved_count = 0
        sqlite_rows = []
        with self._lock:
            for item in records:
                query_text = item.get("query_text", "").strip()
                status = str(item.get("status", "")).strip().upper()
                hazard_level = str(item.get("hazard_level", "")).strip().upper()
                matched_material_ja = str(item.get("matched_material_ja", query_text)).strip()
                matched_material_en = str(item.get("matched_material_en", query_text)).strip()
                confidence = float(item.get("confidence", 0.0))
                reasoning = str(item.get("reasoning", "")).strip()
                source = str(item.get("source", "TIER_5_LLM_ARBITRATION")).strip()

                if status not in ("POSITIVE", "NEGATIVE"):
                    continue
                if confidence < 0.75:
                    continue

                key = self._normalize_key(query_text)
                if not key:
                    continue

                rec = LearnedRecord(
                    query_text=query_text,
                    status=status,
                    hazard_level=hazard_level,
                    matched_material_ja=matched_material_ja,
                    matched_material_en=matched_material_en,
                    confidence=confidence,
                    regulatory_citation=f"{source}: {reasoning}" if reasoning else source,
                    source=source
                )

                self._l1_cache[key] = rec
                saved_count += 1

                if not self.is_json_backend and self._conn is not None:
                    sqlite_rows.append((
                        key,
                        rec.query_text,
                        rec.status,
                        rec.hazard_level,
                        rec.matched_material_ja,
                        rec.matched_material_en,
                        rec.confidence,
                        rec.regulatory_citation,
                        rec.source,
                        rec.learned_at
                    ))

            if persist:
                if self.is_json_backend:
                    self._save_json()
                elif self._conn is not None and sqlite_rows:
                    try:
                        self._conn.executemany(
                            """
                            INSERT OR REPLACE INTO learned_materials 
                            (query_key, query_text, status, hazard_level, matched_material_ja, matched_material_en, confidence, regulatory_citation, source, learned_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            sqlite_rows
                        )
                        self._conn.commit()
                    except Exception as e:
                        logger.error(f"Failed to batch persist learned records to SQLite: {e}")

        logger.info(f"Batch cached {saved_count} learned material records.")
        return saved_count

    def export_to_json(self, json_path: Optional[Path | str] = None) -> int:
        """Exports entire cache to JSON for backups or external tools."""
        target_path = Path(json_path) if json_path else self.DEFAULT_LEGACY_JSON
        with self._lock:
            records_list = [r.model_dump() for r in self._l1_cache.values()]
            payload = {
                "version": "1.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records_list),
                "records": records_list
            }
            target_path.parent.mkdir(parents=True, exist_ok=True)
            temp_file = target_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, target_path)
            logger.info(f"Exported {len(records_list)} learned records to {target_path.name}")
            return len(records_list)

    def get_all(self) -> Dict[str, LearnedRecord]:
        """Returns all cached entries from L1 in-memory cache."""
        with self._lock:
            return dict(self._l1_cache)

    def __len__(self) -> int:
        """Returns the number of cached entries."""
        with self._lock:
            return len(self._l1_cache)

    def close(self) -> None:
        """Closes SQLite database connection."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

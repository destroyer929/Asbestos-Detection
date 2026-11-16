"""
Asbestos Material Knowledge Base Manager.
Integrates Japanese Ministry of Land, Infrastructure, Transport and Tourism (MLIT)
classification standards into an indexed queryable repository.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
import hashlib

from data.database.learned_cache import LearnedMaterialCache, LearnedRecord


HazardLevel = Literal["LEVEL_1", "LEVEL_2", "LEVEL_3", "NON_ASBESTOS", "UNCERTAIN"]
AsbestosStatus = Literal["POSITIVE", "NEGATIVE", "UNCERTAIN"]


class MaterialEntry(BaseModel):
    id: str
    canonical_name_ja: str
    canonical_name_en: str
    synonyms_ja: List[str] = Field(default_factory=list)
    synonyms_en: List[str] = Field(default_factory=list)
    hazard_level: HazardLevel
    status: AsbestosStatus
    friability: str
    component_category: str
    manufacturer: Optional[str] = None
    production_period: Optional[str] = None
    application_locations: List[str] = Field(default_factory=list)
    typical_specifications: List[str] = Field(default_factory=list)
    regulatory_note: str


class MaterialsDatabase:
    """Manages the reference materials database and provides indexing for matching."""

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        learned_cache: Optional[LearnedMaterialCache] = None
    ):
        if db_path is None:
            db_path = Path(__file__).parent / "mlit_materials.json"
        self.db_path = Path(db_path)
        self.entries: List[MaterialEntry] = []
        self._exact_index: Dict[str, MaterialEntry] = {}
        self.learned_cache = learned_cache if learned_cache is not None else LearnedMaterialCache()
        self.load_database()

    def load_database(self) -> None:
        """Loads and indexes the JSON records."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        with open(self.db_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        self.entries = [MaterialEntry(**item) for item in raw_data]
        self._build_indices()

    def _convert_learned_to_entry(self, learned: LearnedRecord) -> MaterialEntry:
        """Converts a LearnedRecord from Tier 5 into a standard MaterialEntry for Tier 1 matching."""
        h = hashlib.md5(learned.query_text.encode("utf-8")).hexdigest()[:8].upper()
        return MaterialEntry(
            id=f"MAT-LEARNED-{h}",
            canonical_name_ja=learned.matched_material_ja or learned.query_text,
            canonical_name_en=learned.matched_material_en or learned.query_text,
            synonyms_ja=[learned.query_text],
            synonyms_en=[],
            hazard_level=learned.hazard_level,
            status=learned.status,
            friability="NONE" if learned.status == "NEGATIVE" else "MOLDED_OR_FRIABLE",
            component_category="Learned Material",
            manufacturer="Field Observed (Learned)",
            production_period="All Eras",
            application_locations=[],
            typical_specifications=[],
            regulatory_note=learned.regulatory_citation
        )

    def _build_indices(self) -> None:
        """Builds lookup dictionaries for instantaneous Tier 1 exact matching."""
        self._exact_index.clear()
        for entry in self.entries:
            # Index canonical names
            self._exact_index[entry.canonical_name_ja.lower().strip()] = entry
            self._exact_index[entry.canonical_name_en.lower().strip()] = entry

            # Index all Japanese synonyms
            for syn in entry.synonyms_ja:
                self._exact_index[syn.lower().strip()] = entry

            # Index all English synonyms
            for syn in entry.synonyms_en:
                self._exact_index[syn.lower().strip()] = entry

        # Supplement index with learned materials from persistent cache
        for key, learned in self.learned_cache.get_all().items():
            learned_entry = self._convert_learned_to_entry(learned)
            self._exact_index[key] = learned_entry
            if learned.matched_material_ja:
                self._exact_index[learned.matched_material_ja.lower().strip()] = learned_entry

    def add_learned_entry(self, learned: LearnedRecord) -> None:
        """Dynamically adds a newly learned material into in-memory Tier 1 index."""
        learned_entry = self._convert_learned_to_entry(learned)
        key = learned.query_text.lower().strip()
        self._exact_index[key] = learned_entry
        if learned.matched_material_ja:
            self._exact_index[learned.matched_material_ja.lower().strip()] = learned_entry

    def exact_lookup(self, query: str) -> Optional[MaterialEntry]:
        """Performs a direct exact string lookup against canonical names and aliases."""
        cleaned = query.strip().lower()
        return self._exact_index.get(cleaned)

    def get_all_entries(self) -> List[MaterialEntry]:
        return self.entries

    def get_by_hazard_level(self, level: HazardLevel) -> List[MaterialEntry]:
        return [e for e in self.entries if e.hazard_level == level]

    def get_asbestos_positive(self) -> List[MaterialEntry]:
        return [e for e in self.entries if e.status == "POSITIVE"]

    def get_non_asbestos(self) -> List[MaterialEntry]:
        return [e for e in self.entries if e.status == "NEGATIVE"]

    def summary(self) -> Dict[str, int]:
        """Returns high-level summary counts for reports and diagnostics."""
        return {
            "total_entries": len(self.entries),
            "level_1_friable": len(self.get_by_hazard_level("LEVEL_1")),
            "level_2_insulation": len(self.get_by_hazard_level("LEVEL_2")),
            "level_3_molded": len(self.get_by_hazard_level("LEVEL_3")),
            "non_asbestos_controls": len(self.get_by_hazard_level("NON_ASBESTOS")),
            "indexed_lookup_keys": len(self._exact_index)
        }


if __name__ == "__main__":
    db = MaterialsDatabase()
    print("Database loaded successfully.")
    print(json.dumps(db.summary(), indent=2, ensure_ascii=False))


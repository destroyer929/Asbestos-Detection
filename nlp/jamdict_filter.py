# Copyright (c) 2026 Karunakar (destroyer929). All rights reserved.
# Proprietary & Confidential. Authorized for technical evaluation and portfolio review only.
"""
Jamdict-Powered Semantic & Linguistic Filter for Japanese Architectural Blueprints.
Uses local JMdict offline dictionary (via jamdict) to inspect English glosses and POS tags.
Filters out:
1. Room and spatial labels (e.g., '便所', '機械室', '更衣室', '倉庫')
2. Construction actions and drawing notes (e.g., '撤去', '補修', '工事', '特記')
3. Non-material structural elements (e.g., '下地', '目地', '巾木')

Guarantees:
- Real materials (e.g., 'モルタル', 'スレート', 'ロックウール', '石綿') are strictly PROTECTED.
- Unregistered proprietary trade names (0 entries in general dictionary, e.g., 'ブロベスト', 'スターベスト')
  are preserved for Tier 5 LLM arbitration.
"""

from __future__ import annotations
import logging
import threading
from typing import Tuple, Optional, Dict, Set

logger = logging.getLogger("alfred.jamdict_filter")

# Semantic gloss keyword triggers for non-material categories
ROOM_GLOSS_KEYWORDS: Set[str] = {
    "room", "restroom", "toilet", "lavatory", "bathroom", "washroom",
    "hall", "corridor", "aisle", "staircase", "stairs", "stairwell",
    "entrance", "exit", "lobby", "foyer", "vestibule", "office",
    "kitchen", "kitchenette", "closet", "storage", "storehouse", "warehouse",
    "garage", "carport", "terrace", "balcony", "veranda", "porch", "patio",
    "roof", "rooftop", "alcove", "cellar", "attic", "basement", "antechamber"
}

ACTION_GLOSS_KEYWORDS: Set[str] = {
    "removal", "withdrawing", "repeal", "repair", "mending", "construction",
    "renovation", "inspection", "demolition", "maintenance", "installation",
    "reinforcement", "cleaning", "specification", "drawing", "scale", "legend",
    "special mention", "detail", "standard", "supervision", "contract"
}

STRUCTURAL_NON_MATERIAL_KEYWORDS: Set[str] = {
    "groundwork", "foundation", "substructure", "joint", "expansion joint",
    "baseboard", "skirting", "sill", "frame", "lintel", "threshold"
}

# Safety whitelist: If a word's gloss mentions any of these, NEVER filter it out as a room or action!
MATERIAL_PROTECTION_KEYWORDS: Set[str] = {
    "asbestos", "mortar", "cement", "slate", "wool", "insulation", "plaster",
    "gypsum", "calcium silicate", "board", "tile", "acoustic", "fiber", "fibre",
    "refractory", "vermiculite", "perlite", "caulk", "sealant", "gasket", "packing"
}


class JamdictLinguisticFilter:
    """
    Offline semantic dictionary filter querying local JMdict database.
    Operates at Gate 4 to eliminate non-material blueprint tokens before Tier-5 LLM.
    """

    _instance: Optional[JamdictLinguisticFilter] = None
    _lock = threading.Lock()

    def __init__(self):
        self._jmd = None
        self._cache: Dict[str, Tuple[bool, str]] = {}
        self._cache_lock = threading.Lock()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> JamdictLinguisticFilter:
        with cls._lock:
            if cls._instance is None:
                cls._instance = JamdictLinguisticFilter()
            return cls._instance

    def _ensure_loaded(self) -> bool:
        if self._initialized:
            return self._jmd is not None

        try:
            from jamdict import Jamdict
            self._jmd = Jamdict()
            self._initialized = True
            logger.info("JamdictLinguisticFilter initialized successfully with local JMdict database.")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Jamdict: {e}. Semantic dictionary filter will be disabled.")
            self._initialized = True
            self._jmd = None
            return False

    def is_non_material(self, text: str) -> Tuple[bool, str]:
        """
        Determines if text represents a non-material entity using dictionary semantics.
        Returns (is_non_material, reason).
        """
        if not text or len(text.strip()) == 0:
            return True, "Empty text"

        query = text.strip()

        # Check in-memory fast cache first
        with self._cache_lock:
            if query in self._cache:
                return self._cache[query]

        if not self._ensure_loaded() or self._jmd is None:
            return False, ""

        try:
            res = self._jmd.lookup(query)
            if not res or not res.entries:
                # 0 entries: could be a proprietary brand name (e.g. ブロベスト) or compound specification.
                # Must NOT be filtered out here — allow Tier 5 to evaluate genuine candidates.
                with self._cache_lock:
                    self._cache[query] = (False, "")
                return False, ""

            # Extract all lowercase glosses
            glosses = [
                g.text.lower()
                for e in res.entries
                for s in e.senses
                for g in s.gloss
            ]

            # 1. Safety check: does it explicitly define a physical building material?
            has_material_gloss = any(
                any(mat in g for mat in MATERIAL_PROTECTION_KEYWORDS)
                for g in glosses
            )
            if has_material_gloss:
                with self._cache_lock:
                    self._cache[query] = (False, "Building material definition confirmed in dictionary")
                return False, "Building material definition confirmed in dictionary"

            # 2. Check for Room / Architectural Space
            for g in glosses:
                for kw in ROOM_GLOSS_KEYWORDS:
                    if kw in g:
                        reason = f"Verified architectural room/space ('{kw}') via JMdict"
                        with self._cache_lock:
                            self._cache[query] = (True, reason)
                        return True, reason

            # 3. Check for Construction Action / Drawing Note
            for g in glosses:
                for kw in ACTION_GLOSS_KEYWORDS:
                    if kw in g:
                        reason = f"Verified construction action/note ('{kw}') via JMdict"
                        with self._cache_lock:
                            self._cache[query] = (True, reason)
                        return True, reason

            # 4. Check for Non-Material Structural Component
            for g in glosses:
                for kw in STRUCTURAL_NON_MATERIAL_KEYWORDS:
                    if kw in g:
                        reason = f"Verified structural non-material element ('{kw}') via JMdict"
                        with self._cache_lock:
                            self._cache[query] = (True, reason)
                        return True, reason

            # Word found in dictionary but neither a prohibited category nor a known material
            with self._cache_lock:
                self._cache[query] = (False, "")
            return False, ""

        except Exception as e:
            logger.warning(f"Error during Jamdict lookup for '{query}': {e}")
            return False, ""


def get_jamdict_filter() -> JamdictLinguisticFilter:
    return JamdictLinguisticFilter.get_instance()

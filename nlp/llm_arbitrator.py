"""
Tier-5 Local LLM Material Arbitrator (Ollama / Qwen2.5-VL-3B).
Resolves UNCERTAIN or low-confidence architectural material annotations
using localized regulatory reasoning under Japanese MLIT (国土交通省)
and Air Pollution Control Act (大気汚染防止法) standards.
"""

from __future__ import annotations
import os
import re
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import requests

from data.database.db_manager import HazardLevel, AsbestosStatus
from nlp.matcher import MatchTier

logger = logging.getLogger("drawing_scan.llm_arbitrator")

# MLIT Asbestos Taxonomy Prompt
MLIT_SYSTEM_PROMPT = """You are an expert Japanese architectural asbestos diagnostic specialist operating under Japan's MLIT (国土交通省) and Air Pollution Control Act (大気汚染防止法) statutory standards.

Your task is to analyze candidate architectural finishing materials from Japanese blueprints (仕上表, 詳細図, 平面図) that could not be confidently identified by classical keyword matching.

For each candidate item:
1. Determine whether the material is POSITIVE for asbestos, NEGATIVE (confirmed non-asbestos), or UNCERTAIN.
2. If POSITIVE, classify its statutory hazard level according to Japanese law:
   - "LEVEL_1": Friable spray materials (吹付けアスベスト, 吹付けロックウール, 吹付けバーミキュライト, スプレーベスト, etc.)
   - "LEVEL_2": Pipe covers, thermal insulation, refractory jackets, lagging (石綿保温材, けい藻土保温材, 耐火被覆板, 配管エルボ, パッキング, etc.)
   - "LEVEL_3": Non-friable molded products / boards (石綿含有成形板, スレート波板, けい酸カルシウム板第1種 / 石綿ケイカル, ビニル床タイル / Pタイル, 押出成形セメント板, 繊維強化セメント板, etc.)
3. If NEGATIVE, classify hazard_level as "NON_ASBESTOS":
   - e.g. グラスウール (GW), ロックウール保温材 (RW - non-asbestos post-2004), せっこうボード / GB-R, けい酸カルシウム板第2種 (無石綿ケイカル), モルタル, 合板, 鋼板, アルミ, コンクリート.
4. If genuinely unknown or insufficient information, set status: "UNCERTAIN", hazard_level: "UNCERTAIN".

Provide the canonical Japanese material name (matched_material_ja), English translation (matched_material_en), confidence (0.0 to 1.0), and a concise regulatory explanation citing MLIT standards.

Respond ONLY with valid JSON in this exact structure:
{
  "results": [
    {
      "id": "ITEM-1",
      "status": "POSITIVE" | "NEGATIVE" | "UNCERTAIN",
      "hazard_level": "LEVEL_1" | "LEVEL_2" | "LEVEL_3" | "NON_ASBESTOS" | "UNCERTAIN",
      "matched_material_ja": "けい酸カルシウム板第1種",
      "matched_material_en": "Asbestos Calcium Silicate Board Type 1",
      "confidence": 0.95,
      "reasoning": "石綿ケイカル is common shorthand for Level 3 molded Asbestos Calcium Silicate Board Type 1 under MLIT standards."
    }
  ]
}
"""

VALID_STATUSES = {"POSITIVE", "NEGATIVE", "UNCERTAIN"}
VALID_HAZARD_LEVELS = {"LEVEL_1", "LEVEL_2", "LEVEL_3", "NON_ASBESTOS", "UNCERTAIN"}


class LocalLLMArbitrator:
    """
    Tier-5 Arbitrator communicating with a local Ollama instance (default: qwen2.5vl:3b).
    Operates resiliently with timeout protection and non-blocking offline fallbacks.
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 45.0,
        temperature: float = 0.1,
        enabled: bool = True
    ):
        self.ollama_url = (ollama_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5vl:3b")
        self.timeout = timeout
        self.temperature = temperature
        self.enabled = enabled

        # Cache availability status to avoid repeated HTTP calls when offline
        self._last_health_check_time: float = 0.0
        self._is_available: bool = False
        self._health_ttl: float = 30.0  # seconds

    def is_available(self, force_refresh: bool = False) -> bool:
        """Checks if local Ollama server is running and the target model is loaded/available."""
        if not self.enabled:
            return False

        now = time.time()
        if not force_refresh and (now - self._last_health_check_time) < self._health_ttl:
            return self._is_available

        self._last_health_check_time = now
        try:
            res = requests.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check exact or partial match (e.g. 'qwen2.5vl:3b' in 'qwen2.5vl:3b')
                target_base = self.model_name.split(":")[0]
                matched = any(self.model_name in m or target_base in m for m in models)
                self._is_available = matched
                if not matched:
                    logger.warning(
                        f"Ollama running but model '{self.model_name}' not found in installed models: {models}"
                    )
                return self._is_available
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            self._is_available = False
            return False

        self._is_available = False
        return False

    def arbitrate_batch(
        self,
        candidate_items: List[Dict[str, Any]],
        max_batch_size: int = 8
    ) -> Dict[str, Dict[str, Any]]:
        """
        Sends a batch of uncertain items to the local LLM for MLIT statutory arbitration.
        Returns a dictionary mapping item_id -> parsed arbitration result.
        """
        if not candidate_items or not self.is_available():
            return {}

        results_by_id: Dict[str, Dict[str, Any]] = {}

        # Process in sub-batches if necessary to prevent context blowup
        for i in range(0, len(candidate_items), max_batch_size):
            chunk = candidate_items[i : i + max_batch_size]
            chunk_results = self._process_chunk(chunk)
            results_by_id.update(chunk_results)

        return results_by_id

    def _process_chunk(self, items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Processes a single chunk of candidate items via Ollama API."""
        formatted_items = []
        for it in items:
            formatted_items.append({
                "id": it.get("item_id") or it.get("id"),
                "raw_text": it.get("raw_text") or it.get("text", ""),
                "normalized_text": it.get("normalized_text", ""),
                "room_context": it.get("room_context") or it.get("room", ""),
                "region_type": it.get("region_type") or it.get("region", "")
            })

        user_content = f"Classify the following candidate architectural drawing items:\n{json.dumps(formatted_items, ensure_ascii=False, indent=2)}"

        payload = {
            "model": self.model_name,
            "prompt": f"{MLIT_SYSTEM_PROMPT}\n\n{user_content}",
            "format": "json",
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        try:
            logger.info(f"Submitting {len(items)} items to local LLM ({self.model_name}) for Tier-5 arbitration...")
            t0 = time.time()
            res = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            elapsed = time.time() - t0
            logger.info(f"LLM arbitration completed in {elapsed:.2f}s (status: {res.status_code})")

            if res.status_code != 200:
                logger.error(f"Ollama returned HTTP {res.status_code}: {res.text}")
                return {}

            resp_json = res.json()
            raw_response = resp_json.get("response", "").strip()

            return self._parse_llm_json(raw_response)

        except requests.Timeout:
            logger.warning(f"Local LLM arbitration timed out after {self.timeout}s.")
            return {}
        except Exception as e:
            logger.warning(f"Local LLM arbitration request failed: {e}")
            return {}

    def _parse_llm_json(self, raw_text: str) -> Dict[str, Dict[str, Any]]:
        """Robustly parses LLM JSON response into a normalized dictionary."""
        parsed_dict: Dict[str, Dict[str, Any]] = {}
        if not raw_text:
            return parsed_dict

        data = None
        # Direct parse attempt
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Fallback regex extraction of JSON block
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

        if not data:
            logger.warning(f"Failed to parse JSON from LLM response: {raw_text[:200]}")
            return parsed_dict

        results_list = []
        if isinstance(data, dict):
            results_list = data.get("results", [])
            if not results_list and "items" in data:
                results_list = data.get("items", [])
        elif isinstance(data, list):
            results_list = data

        for entry in results_list:
            if not isinstance(entry, dict):
                continue
            item_id = entry.get("id")
            if not item_id:
                continue

            status = str(entry.get("status", "UNCERTAIN")).strip().upper()
            if status not in VALID_STATUSES:
                status = "UNCERTAIN"

            hazard_level = str(entry.get("hazard_level", "UNCERTAIN")).strip().upper()
            if hazard_level not in VALID_HAZARD_LEVELS:
                hazard_level = "UNCERTAIN"

            # Cross-validate status and hazard_level
            if status == "NEGATIVE" and hazard_level != "NON_ASBESTOS":
                hazard_level = "NON_ASBESTOS"
            elif status == "POSITIVE" and hazard_level not in {"LEVEL_1", "LEVEL_2", "LEVEL_3"}:
                hazard_level = "LEVEL_3"

            try:
                conf = float(entry.get("confidence", 0.85))
            except (ValueError, TypeError):
                conf = 0.85
            conf = max(0.0, min(1.0, conf))

            parsed_dict[item_id] = {
                "id": item_id,
                "status": status,
                "hazard_level": hazard_level,
                "matched_material_ja": entry.get("matched_material_ja", "不明 (Uncertain)"),
                "matched_material_en": entry.get("matched_material_en", entry.get("matched_material_ja", "")),
                "confidence": conf,
                "reasoning": entry.get("reasoning", "MLIT regulatory arbitration.")
            }

        return parsed_dict

    def arbitrate_diagnoses(
        self,
        diagnoses: List[Any],
        confidence_threshold: float = 0.70
    ) -> List[Any]:
        """
        Takes a list of DrawingItemDiagnosis objects from the 4-tier classifier,
        identifies UNCERTAIN items, arbitrates them with the local LLM, and updates them in-place.
        """
        if not self.is_available():
            logger.debug("Local LLM Arbitrator is unavailable. Keeping 4-tier determinations.")
            return diagnoses

        uncertain_items = [
            d for d in diagnoses
            if getattr(d, "status", None) == "UNCERTAIN" or getattr(d, "match_tier", None) == "NO_MATCH"
        ]

        if not uncertain_items:
            return diagnoses

        logger.info(f"Routing {len(uncertain_items)} UNCERTAIN item(s) to Tier-5 LLM Arbitrator...")

        items_payload = [
            {
                "item_id": d.item_id,
                "raw_text": d.raw_text,
                "normalized_text": d.normalized_text,
                "room_context": d.room_context,
                "region_type": d.region_type
            }
            for d in uncertain_items
        ]

        llm_results = self.arbitrate_batch(items_payload)

        for d in uncertain_items:
            res = llm_results.get(d.item_id)
            if not res:
                continue

            # Only accept high-confidence resolutions
            if res["confidence"] >= confidence_threshold and res["status"] in ("POSITIVE", "NEGATIVE"):
                d.status = res["status"]
                d.hazard_level = res["hazard_level"]
                d.matched_material_ja = res["matched_material_ja"]
                d.matched_material_en = res.get("matched_material_en") or res["matched_material_ja"]
                d.confidence = res["confidence"]
                d.match_tier = MatchTier.TIER_5_LLM.value
                d.regulatory_citation = f"[Tier-5 LLM: {self.model_name}] {res['reasoning']}"

                # Safety triage rules:
                # 1. Any Level 1 positive always requires human review
                # 2. Confidence below 0.85 requires review
                # 3. High-confidence Negative or Level 3 clear matches pass triage
                if d.status == "POSITIVE" and d.hazard_level == "LEVEL_1":
                    d.requires_human_review = True
                elif d.confidence < 0.85:
                    d.requires_human_review = True
                else:
                    d.requires_human_review = False

                logger.info(
                    f"Resolved {d.item_id} ('{d.raw_text}') -> {d.status} [{d.hazard_level}] ({d.matched_material_ja}) via Tier-5 LLM"
                )
            else:
                # Retain UNCERTAIN status and append LLM reasoning if available
                if res.get("reasoning"):
                    d.regulatory_citation = f"[Tier-5 LLM UNCERTAIN] {res['reasoning']}"

        return diagnoses


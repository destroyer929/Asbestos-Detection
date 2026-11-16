"""
Tier-5 Local LLM Material Arbitrator (Ollama / Qwen3:1.7B).
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
from typing import List, Dict, Any, Optional, Tuple, Callable
import requests

from data.database.db_manager import HazardLevel, AsbestosStatus
from nlp.matcher import MatchTier

logger = logging.getLogger("drawing_scan.llm_arbitrator")

# MLIT Asbestos Taxonomy & 3-Way Triage Prompt
MLIT_SYSTEM_PROMPT = """You are an expert Japanese architectural asbestos diagnostic specialist operating under Japan's MLIT (国土交通省) and Air Pollution Control Act (大気汚染防止法) statutory standards.

Your task is to analyze candidate architectural finishing materials from Japanese blueprints (仕上表, 詳細図, 平面図) that could not be confidently identified by classical keyword matching.

Perform 3-way triage for each item:

1. POSITIVE (Hazardous Asbestos Material):
   - Confirmed hazardous asbestos materials, historical asbestos products, or common Japanese asbestos abbreviations/slang:
     * LEVEL_1: Friable spray materials (吹付けアスベスト, 吹付けロックウール, 吹付けバーミキュライト, スプレーベスト, etc.)
     * LEVEL_2: Pipe covers, thermal insulation, refractory jackets, lagging (石綿保温材, けい藻土保温材, 耐火被覆板, 配管エルボ, パッキング, etc.)
     * LEVEL_3: Non-friable molded products / boards (石綿含有成形板, スレート波板, けい酸カルシウム板第1種 / 石綿ケイカル, ビニル床タイル / Pタイル, 押出成形セメント板, 繊維強化セメント板, etc.)
   - status: "POSITIVE"
   - review_required: true (for LEVEL_1 friable spray or confidence < 0.85), false (for standard LEVEL_2/3)

2. NEGATIVE (Confirmed Non-Asbestos - Normal Building Elements & Everyday Words):
   - Group 2A: Safe standard construction materials without asbestos (e.g. グラスウール / GW, ロックウール保温材 / RW post-2004, せっこうボード / GB-R, プラスターボード, けい酸カルシウム板第2種, モルタル, 木製巾木, 磁器質タイル, タイル巾木, コンクリート, 合板, 鋼板, アルミ, ガラス, 塗料仕上げ).
   - Group 2B: Common everyday words, room/space/office names, general specifications, drawing notes, and municipal titles that are completely unrelated to asbestos:
     * Room / place names: 機械室, 事務室, 倉庫, 給湯室, ボイラー室, 廊下, ホール, 便所, トイレ, 会議室, 更衣室, 階段室, EVホール, 湯沸室, 控室, etc.
     * Common architectural specifications / notes: 耐水, 耐水仕様, 防音仕様, 保温要, 一般部, なし, 特記, 仕様, 標準, 特記なき限り, etc.
     * Municipal titles / drawing headers: 流山市, 工中名称, 仕上表, 仕上リスト, 設計, 施工, etc.
   - For ALL Group 2A and Group 2B items, you MUST output:
     * status: "NEGATIVE"
     * hazard_level: "NON_ASBESTOS"
     * review_required: false
     * confidence: 0.95 to 1.0

3. UNCERTAIN (Unique Brand Names, Ambiguous Trade Products, or Genuine Unknowns):
   - ONLY for rare proprietary trade names, unknown manufacturer product brands (e.g. obscure 1970s commercial brand names, cryptic product codes like 'ハイベストX', 'ダンパック', custom composite panels), or ambiguous strings where asbestos content cannot be safely ruled out.
   - Or when you genuinely cannot determine the meaning or safety of the material.
   - status: "UNCERTAIN"
   - hazard_level: "UNCERTAIN"
   - review_required: true
   - confidence: 0.0 to 0.5

Respond ONLY with valid JSON in this exact structure:
{
  "results": [
    {
      "id": "ITEM-1",
      "status": "POSITIVE" | "NEGATIVE" | "UNCERTAIN",
      "hazard_level": "LEVEL_1" | "LEVEL_2" | "LEVEL_3" | "NON_ASBESTOS" | "UNCERTAIN",
      "matched_material_ja": "string",
      "matched_material_en": "string",
      "review_required": boolean,
      "confidence": float,
      "reasoning": "Concise explanation in Japanese or English citing MLIT standards"
    }
  ]
}
"""

VALID_STATUSES = {"POSITIVE", "NEGATIVE", "UNCERTAIN"}
VALID_HAZARD_LEVELS = {"LEVEL_1", "LEVEL_2", "LEVEL_3", "NON_ASBESTOS", "UNCERTAIN"}

ARCHITECTURAL_SHORTHAND = {
    "PB", "ALC", "EP", "VP", "RC", "PC", "OP", "DP", "A種", "B種",
    "F板", "石綿", "合板", "波板", "直押", "金ゴテ", "なし", "同上",
    "けい酸", "ケイカル", "フレキ", "コロニアル", "カラーベスト", "モルタル", "プラスター",
    "GW", "RW", "LGS", "ECP", "CF", "CFシート", "岩綿", "スレート", "せっこうボード", "石膏ボード"
}

# Material indicators (affixes, compound stems, and specification tokens)
MATERIAL_AFFIXES = {
    "材", "板", "吹付", "吹き", "保温", "被覆", "吸音", "断熱", "スレート", "フェルト",
    "ロック", "ウール", "綿", "石綿", "アスベスト", "パネル", "シート", "タイル", "ボード",
    "モルタル", "プラスター", "クロス", "塗装", "ペイント", "リシン", "スタッコ",
    "パーライト", "バーミキュライト", "ケイカル", "けい酸", "石膏", "せっこう",
    "ルーフィング", "パッキン", "ガスケット", "シーリング", "コーキング", "目地", "仕上", "仕上げ"
}

# Known drawing metadata, room types, and non-material keywords that should never be sent to the LLM
KNOWN_NON_MATERIAL_TERMS = {
    "流山市", "工中名称", "仕上リスト", "特記仕上表", "外部仕上表", "内部仕上表", "図面名称", "縮尺", "設計", "施工",
    "室", "室名", "腰", "腰壁", "壁", "柱", "型", "梁型", "天", "井", "天井", "床", "巾木", "下地", "備考",
    "屋根", "庇", "外壁", "内壁", "パラペット", "基礎", "構造", "凡例", "特記", "一般部", "保温要", "耐水",
    "防音仕様", "耐震改修", "平面詳細図", "立面図", "断面図", "配置図", "案内図", "特記事項"
}

ROOM_SUFFIX_PATTERN = re.compile(
    r"^(.*)(室|所|庫|ホール|廊下|階段|玄関|エントランス|シャフト|ピロティ|屋上|バルコニー|テラス|風除室|トイレ|便所)[\s\(（]?.*[\)）]?$"
)

KATAKANA_BRAND_PATTERN = re.compile(r"[\u30a1-\u30fa\u30fc]{3,}")


def is_valid_material_candidate(text: str) -> bool:
    """
    GATE 4: Tier-5 Safety Gate (Strict Japanese Character & Material Filter).
    Ensures that ONLY genuine ambiguous Japanese architectural materials (or obscure trade names)
    are submitted to the local LLM. Room names, building sections, execution specifications,
    and dimension/symbol noise are safely auto-resolved as NEGATIVE (Zero Ollama calls).
    """
    if not text or len(text.strip()) == 0:
        return False

    # Strip unprintable control characters and mojibake blocks
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f\u0250-\u02af\u1c80-\u1cbf\u1cd0-\u1cff]', '', text).strip()
    if not cleaned or len(cleaned) == 0:
        return False

    # Whitelist check: If it's a known architectural shorthand, it's valid
    if cleaned.upper() in ARCHITECTURAL_SHORTHAND or any(sh == cleaned for sh in ARCHITECTURAL_SHORTHAND):
        return True

    # Punctuation & bracket strip for core analysis
    cleaned_pure = re.sub(r"^[\s:;,\-\.\'\"（(【\[\)=~`\*\[\]{}<>]+", "", cleaned)
    cleaned_pure = re.sub(r"[\s:;,\-\.\'\"）)】\]\)=~`\*\[\]{}<>]+$", "", cleaned_pure).strip()
    if not cleaned_pure:
        return False

    # Filter out pure numbers, dimensions, CAD coordinates, and mixed math symbols
    # (e.g. '1* 790', '089 *1', 'X1a', '(4)', '009 °5', '2.70g', 'L--10', 'W00,D150.H1', '005×00')
    if re.match(r"^[\d\s.,\*\+~=\-°/%×€$¥#@&_:\(\)\[\]\{\}<>\'\"\\a-zA-Z]+$", cleaned):
        return False

    # Must contain Japanese script (Kanji, Katakana, Hiragana)
    japanese_chars = re.findall(r"[\u4e00-\u9fff\u30a0-\u30ff\u3040-\u309f]", cleaned_pure)
    if not japanese_chars:
        return False

    # Filter out isolated 1-character fragments (e.g. '什', '百', '是', '品', '国', '中', '日', '土', '号', '工')
    # unless explicitly "石綿"
    if len(japanese_chars) <= 1 and "".join(japanese_chars) != "石綿":
        return False

    # Known drawing title / municipality keywords / non-material terms
    if cleaned in KNOWN_NON_MATERIAL_TERMS or cleaned_pure in KNOWN_NON_MATERIAL_TERMS:
        return False

    # Check for room label without material indicators
    has_material_indicator = (
        any(aff in cleaned for aff in MATERIAL_AFFIXES)
        or bool(re.search(r"t\s*=\s*\d+", cleaned))
        or bool(re.search(r"\d+\s*mm", cleaned))
    )
    if not has_material_indicator:
        if ROOM_SUFFIX_PATTERN.match(cleaned_pure):
            return False

    # Genuine Ambiguous Material Check (Diagram Gate 4):
    # Must have either a physical material affix/specification OR a 3+ Katakana trade name pattern
    has_katakana_trade = bool(KATAKANA_BRAND_PATTERN.search(cleaned_pure))
    if not (has_material_indicator or has_katakana_trade):
        return False

    return True


class UnidentifiedMaterialMap:
    """
    In-memory Map / Trie data structure tracking unidentified / ambiguous material
    annotations across multiple pages of an architectural blueprint.

    Deduplicates identical material names across multiple occurrences and pages while
    preserving all unique spatial coordinates (bbox, polygon), page numbers, room contexts,
    and item IDs. Enables single-query batch arbitration to the local LLM and broadcasts
    the arbitrated determinations back to all recorded coordinate locations.
    """

    def __init__(self):
        # Map: clean_key -> dict with metadata and list of diagnosis instances
        self._map: Dict[str, Dict[str, Any]] = {}
        # Mapping from query ID (e.g. MAT-0001) back to clean_key
        self._id_to_key: Dict[str, str] = {}
        # Mapping from clean_key to query ID
        self._key_to_id: Dict[str, str] = {}

    @staticmethod
    def normalize_key(text: str) -> str:
        """Normalizes candidate text for deduplication across pages."""
        if not text:
            return ""
        # Strip outer whitespace and collapse multiple internal whitespace
        cleaned = re.sub(r"\s+", " ", text.strip())
        return cleaned

    def add(self, diagnosis: Any) -> None:
        """
        Registers an unidentified diagnosis occurrence into the map.
        Preserves coordinates, page number, room context, and item_id.
        """
        raw_text = getattr(diagnosis, "raw_text", "") or ""
        norm_text = getattr(diagnosis, "normalized_text", "") or ""

        # Primary key from normalized text, fallback to raw text
        clean_key = self.normalize_key(norm_text) or self.normalize_key(raw_text)
        if not clean_key:
            clean_key = raw_text.strip() or "UNKNOWN_MATERIAL"

        if clean_key not in self._map:
            mat_id = f"MAT-{len(self._map) + 1:04d}"
            self._map[clean_key] = {
                "id": mat_id,
                "key": clean_key,
                "raw_text": raw_text,
                "normalized_text": norm_text,
                "instances": [],
                "page_numbers": set(),
                "locations": []  # list of {item_id, page_number, bbox, room_context}
            }
            self._id_to_key[mat_id] = clean_key
            self._key_to_id[clean_key] = mat_id

        entry = self._map[clean_key]
        entry["instances"].append(diagnosis)
        page_num = getattr(diagnosis, "page_number", 1)
        entry["page_numbers"].add(page_num)
        entry["locations"].append({
            "item_id": getattr(diagnosis, "item_id", ""),
            "page_number": page_num,
            "bbox": getattr(diagnosis, "bbox", []),
            "room_context": getattr(diagnosis, "room_context", "")
        })

    def get_unique_payload(self) -> List[Dict[str, Any]]:
        """
        Generates deduplicated payload for Tier-5 LLM batch arbitration.
        Aggregates room contexts across occurrences so the LLM has complete context.
        """
        payload = []
        for key, entry in self._map.items():
            instances = entry["instances"]
            first_inst = instances[0]
            # Aggregate unique non-empty room contexts across all occurrences
            unique_rooms = sorted({
                getattr(d, "room_context", "")
                for d in instances
                if getattr(d, "room_context", "")
            })
            room_context_str = ", ".join(unique_rooms) if unique_rooms else getattr(first_inst, "room_context", "")

            payload.append({
                "item_id": entry["id"],
                "raw_text": entry["raw_text"],
                "normalized_text": entry["normalized_text"],
                "room_context": room_context_str,
                "region_type": getattr(first_inst, "region_type", "GENERAL_NOTES")
            })
        return payload

    def broadcast_results(
        self,
        llm_results: Dict[str, Dict[str, Any]],
        model_name: str
    ) -> int:
        """
        Broadcasts LLM arbitration determinations to ALL recorded instances across all pages.
        Returns the number of individual diagnosis instances updated.
        """
        updated_count = 0
        for mat_id, res in llm_results.items():
            clean_key = self._id_to_key.get(mat_id)
            if not clean_key or clean_key not in self._map:
                continue

            entry = self._map[clean_key]
            instances = entry["instances"]

            status = res.get("status", "UNCERTAIN")
            hazard_level = res.get("hazard_level", "UNCERTAIN")
            mat_ja = res.get("matched_material_ja", "")
            mat_en = res.get("matched_material_en", "")
            conf = res.get("confidence", 0.0)
            reasoning = res.get("reasoning", "")
            review_req = res.get("review_required", False)

            for d in instances:
                # Case 1: NEGATIVE - Confirmed non-asbestos materials, everyday words, room names, or general specs
                if status == "NEGATIVE":
                    d.status = "NEGATIVE"
                    d.hazard_level = "NON_ASBESTOS"
                    d.matched_material_ja = mat_ja or d.raw_text
                    d.matched_material_en = mat_en or d.raw_text
                    d.confidence = max(0.90, conf)
                    d.match_tier = MatchTier.TIER_5_LLM.value
                    d.regulatory_citation = f"[Tier-5 LLM: {model_name}] {reasoning}"
                    d.requires_human_review = False
                    logger.info(
                        f"Resolved {d.item_id} (Page {getattr(d, 'page_number', 1)}, '{d.raw_text}') -> NEGATIVE [NON_ASBESTOS] ({d.matched_material_ja}) via Tier-5 LLM"
                    )

                # Case 2: POSITIVE - Confirmed MLIT statutory asbestos materials
                elif status == "POSITIVE" and hazard_level in ("LEVEL_1", "LEVEL_2", "LEVEL_3"):
                    d.status = "POSITIVE"
                    d.hazard_level = hazard_level
                    d.matched_material_ja = mat_ja
                    d.matched_material_en = mat_en or mat_ja
                    d.confidence = max(0.85, conf)
                    d.match_tier = MatchTier.TIER_5_LLM.value
                    d.regulatory_citation = f"[Tier-5 LLM: {model_name}] {reasoning}"
                    if hazard_level == "LEVEL_1" or d.confidence < 0.85 or review_req:
                        d.requires_human_review = True
                    else:
                        d.requires_human_review = False
                    logger.info(
                        f"Resolved {d.item_id} (Page {getattr(d, 'page_number', 1)}, '{d.raw_text}') -> POSITIVE [{d.hazard_level}] ({d.matched_material_ja}) via Tier-5 LLM"
                    )

                # Case 3: UNCERTAIN - Unique brand names, ambiguous proprietary codes, or fallback
                else:
                    d.status = "UNCERTAIN"
                    d.hazard_level = "UNCERTAIN"
                    d.matched_material_ja = mat_ja if mat_ja and "None" not in mat_ja else "未特定商標・要確認"
                    d.matched_material_en = mat_en if mat_en and "None" not in mat_en else "Unidentified Brand / Review Required"
                    d.confidence = conf
                    d.match_tier = MatchTier.TIER_5_LLM.value
                    d.regulatory_citation = f"[Tier-5 LLM Review Needed: {model_name}] {reasoning or 'Unique brand name or ambiguous material requiring human expert verification.'}"
                    d.requires_human_review = True
                    logger.info(
                        f"Flagged {d.item_id} (Page {getattr(d, 'page_number', 1)}, '{d.raw_text}') -> UNCERTAIN (Human Review Required) via Tier-5 LLM"
                    )

                updated_count += 1

        return updated_count

    @property
    def total_unique(self) -> int:
        return len(self._map)

    @property
    def total_occurrences(self) -> int:
        return sum(len(entry["instances"]) for entry in self._map.values())


class LocalLLMArbitrator:
    """
    Tier-5 Arbitrator communicating with a local Ollama instance (default: qwen3:1.7b).
    Operates resiliently with timeout protection and non-blocking offline fallbacks.
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 35.0,
        temperature: float = 0.1,
        enabled: bool = True
    ):
        self.ollama_url = (ollama_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
        self.timeout = timeout
        self.temperature = temperature
        self.enabled = enabled
        self.last_material_map: Optional[UnidentifiedMaterialMap] = None

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
        max_batch_size: int = 6,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Sends a batch of uncertain items to the local LLM for MLIT statutory arbitration.
        Processes in sub-batches (default 6) and emits real-time progress callbacks.
        Returns a dictionary mapping item_id -> parsed arbitration result.
        """
        if not candidate_items or not self.is_available():
            return {}

        results_by_id: Dict[str, Dict[str, Any]] = {}
        total = len(candidate_items)
        completed = 0

        # Process in sub-batches of 6 items with live progress reporting
        for i in range(0, total, max_batch_size):
            chunk = candidate_items[i : i + max_batch_size]
            curr_text = chunk[0].get("raw_text") or chunk[0].get("text", "")
            if progress_callback:
                progress_callback({
                    "stage": "finalize",
                    "total": total,
                    "completed": completed,
                    "current": curr_text,
                    "message": f"Arbitrating ({completed}/{total}): {curr_text}"
                })

            chunk_results = self._process_chunk(chunk)
            results_by_id.update(chunk_results)
            completed = min(total, completed + len(chunk))

            last_text = chunk[-1].get("raw_text") or chunk[-1].get("text", "")
            if progress_callback:
                progress_callback({
                    "stage": "finalize",
                    "total": total,
                    "completed": completed,
                    "current": last_text,
                    "message": f"Arbitrated {completed} of {total} materials"
                })

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
                "temperature": self.temperature,
                "num_predict": 2048
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
                "review_required": bool(entry.get("review_required", status == "UNCERTAIN")),
                "confidence": conf,
                "reasoning": entry.get("reasoning", "MLIT regulatory arbitration.")
            }

        return parsed_dict

    def arbitrate_diagnoses(
        self,
        diagnoses: List[Any],
        confidence_threshold: float = 0.70,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> List[Any]:
        """
        Takes a list of DrawingItemDiagnosis objects from the 4-tier classifier,
        identifies UNCERTAIN items, arbitrates them with the local LLM, and updates them in-place.
        Supports live progress reporting for Tier-5 processing counts.
        """
        if not self.is_available():
            logger.debug("Local LLM Arbitrator is unavailable. Keeping 4-tier determinations.")
            if progress_callback:
                progress_callback({
                    "stage": "finalize",
                    "total": 0,
                    "completed": 0,
                    "current": "",
                    "message": "Tier-5 LLM offline; keeping 4-tier determinations."
                })
            return diagnoses

        uncertain_items = [
            d for d in diagnoses
            if getattr(d, "status", None) == "UNCERTAIN" or getattr(d, "match_tier", None) == "NO_MATCH"
        ]

        if not uncertain_items:
            if progress_callback:
                progress_callback({
                    "stage": "finalize",
                    "total": 0,
                    "completed": 0,
                    "current": "",
                    "message": "All items resolved in Tiers 1-4 (0 items required Tier-5)."
                })
            return diagnoses

        # Pre-filtering: identify candidate annotations vs obvious non-material noise
        valid_candidates = []
        for d in uncertain_items:
            if is_valid_material_candidate(d.raw_text):
                valid_candidates.append(d)
            else:
                # Obvious dimensions, punctuation, rooms, or general specs are auto-resolved as non-asbestos
                d.status = "NEGATIVE"
                d.hazard_level = "NON_ASBESTOS"
                d.matched_material_ja = d.raw_text
                d.matched_material_en = "Non-Material Architectural Entity (Non-Asbestos)"
                d.confidence = 1.0
                d.match_tier = MatchTier.TIER_5_LLM.value
                d.regulatory_citation = "Non-material architectural entity, room label, or general specification auto-resolved as non-asbestos (Zero Ollama calls)."
                d.requires_human_review = False

        total_cand = len(valid_candidates)
        if total_cand == 0:
            if progress_callback:
                progress_callback({
                    "stage": "finalize",
                    "total": 0,
                    "completed": 0,
                    "current": "",
                    "message": "Non-material noise filtered; 0 candidate materials sent to Tier-5."
                })
            return diagnoses

        # Build In-Memory Map of Unidentified Materials (Deduplication across pages & locations)
        material_map = UnidentifiedMaterialMap()
        for d in valid_candidates:
            material_map.add(d)

        self.last_material_map = material_map
        total_unique = material_map.total_unique
        total_occurrences = material_map.total_occurrences

        logger.info(
            f"Deduplication map: {total_occurrences} occurrence(s) across drawing grouped into "
            f"{total_unique} unique candidate material(s) for Tier-5 LLM ({self.model_name})."
        )

        unique_payload = material_map.get_unique_payload()

        if progress_callback:
            progress_callback({
                "stage": "finalize",
                "total": total_unique,
                "completed": 0,
                "current": unique_payload[0]["raw_text"] if unique_payload else "",
                "message": f"Deduplicated {total_occurrences} candidates into {total_unique} unique materials for Tier-5 LLM ({self.model_name})"
            })

        llm_results = self.arbitrate_batch(
            unique_payload,
            max_batch_size=6,
            progress_callback=progress_callback
        )

        # Broadcast LLM decisions back to all coordinate instances across all pages
        updated_count = material_map.broadcast_results(llm_results, self.model_name)
        logger.info(f"Broadcasted Tier-5 LLM determinations to {updated_count} location instance(s).")

        return diagnoses


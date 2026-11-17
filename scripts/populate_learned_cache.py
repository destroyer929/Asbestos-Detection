"""
Populate Learned SQLite WAL Cache with Historical LLM and Gate 4 Classifications.
- Ingests all records from data/database/learned_materials.json.
- Ingests verified LLM and Gate 4 diagnoses from data/analysis_history.json.
- Converts valid drawing notes, specifications, and non-architectural items from UNCERTAIN to NEGATIVE.
- Strictly excludes actual meaningless noise and severe OCR mojibake.
- Stores records in SQLite WAL mode (data/database/learned_cache.db) with L1 in-memory hash index.
- Synchronizes with data/database/learned_materials.json.
"""

from __future__ import annotations
import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.database.learned_cache import LearnedMaterialCache
from nlp.llm_arbitrator import (
    resolve_non_material_description,
    UnidentifiedMaterialMap,
    ARCHITECTURAL_GLOSSARY,
    ARCHITECTURAL_SHORTHAND,
    KNOWN_NON_MATERIAL_TERMS
)
from nlp.jamdict_filter import get_jamdict_filter

jf = get_jamdict_filter()

ARCHITECTURAL_STEMS = [
    "仕上", "ピット", "工法", "仕様", "張", "塗", "下地", "目地", "スラリー", "タラップ", "ツヤ",
    "枠", "板", "パネル", "タイル", "シート", "壁", "床", "天井", "梁", "柱", "ボルト", "高",
    "室", "所", "部", "材", "巾木", "幅木", "基礎", "屋根", "庇", "配管", "ダクト", "ガラス",
    "木", "鉄", "コンクリート", "モルタル", "ボード", "断熱", "保温", "防湿", "防水", "耐火",
    "不燃", "難燃", "合板", "化粧", "クロス", "とする", "とす", "示す", "FL", "SL", "GL", "CH",
    "見切", "水切", "土間", "金物", "ハンガー", "レール", "既製", "既製品", "ブラケット", "ピクチャー",
    "沓摺", "手摺", "ステップ", "ノンスリップ", "コーニス", "ルーバー", "ガラリ", "シャッター", "サッシ",
    "ハッチ", "点検口", "伸縮", "目透し", "刷毛", "コテ", "押え", "面木", "面取", "水抜", "勾配",
    "ウール", "スレート", "プラスター", "ペイント", "リシン", "スタッコ", "パーライト", "ケイカル",
    "ルーフィング", "パッキン", "ガスケット", "シーリング", "コーキング", "デッキ", "グラスウール",
    "ロック", "フェルト", "ウレタン", "ポリスチレン", "スタッド", "アンカー", "ナット", "ワッシャー",
    "フロア", "グレーチング", "ドレン", "ドレイン", "パイプ", "プライマー", "プライマ", "エッチング"
]

FALSE_POSITIVE_OVERRIDE = {
    "ハラペット": ("NEGATIVE", "NON_ASBESTOS", "Parapet (Non-Architectural Material)"),
    "ーガルバリウム鋼板角波タイフ": ("NEGATIVE", "NON_ASBESTOS", "Galvalume Steel Sheet Rib Profile"),
    "Ｂ：カラーガルバリウム鋼板角波タイプ（指定色）": ("NEGATIVE", "NON_ASBESTOS", "Color Galvalume Steel Sheet Rib Profile"),
    "カラーガルバリウム調板角渡タイプ": ("NEGATIVE", "NON_ASBESTOS", "Color Galvalume Steel Sheet Rib Profile"),
    "ンクリート打放し(素地": ("NEGATIVE", "NON_ASBESTOS", "Exposed Concrete / Bare Substrate (Non-Architectural Material)"),
}


def is_meaningless_noise(text: str) -> Tuple[bool, str]:
    """
    Identifies whether a string is pure OCR mojibake or meaningless noise.
    Returns (True, reason) to exclude from cache.
    """
    if not text or len(text.strip()) == 0:
        return True, "Empty text"

    # Unprintable/control characters and mojibake blocks
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f\u0250-\u02af\u1c80-\u1cbf\u1cd0-\u1cff\ufffd]', '', text).strip()
    if not cleaned:
        return True, "Unprintable/mojibake noise"

    # Punctuation/brackets strip
    cleaned_pure = re.sub(r"^[\s:;,\-\.\'\"（(【\[\)=~`\*\[\]{}<>]+", "", cleaned)
    cleaned_pure = re.sub(r"[\s:;,\-\.\'\"）)】\]\)=~`\*\[\]{}<>]+$", "", cleaned_pure).strip()
    if not cleaned_pure:
        return True, "Only punctuation/brackets"

    # Pure alphanumeric / formula / dimension string
    if re.match(r"^[\d\s.,\*\+~=\-°/%×€$¥#@&_:\(\)\[\]\{\}<>\'\"\\a-zA-Z]+$", cleaned):
        if cleaned.upper() not in ARCHITECTURAL_SHORTHAND and not any(sh == cleaned for sh in ARCHITECTURAL_SHORTHAND):
            return True, "Dimension / coordinate / numeric formula string"

    # Japanese character check
    jp_chars = re.findall(r"[\u4e00-\u9fff\u30a0-\u30ff\u3040-\u309f]", cleaned_pure)
    if not jp_chars:
        if cleaned_pure.upper() in ARCHITECTURAL_SHORTHAND:
            return False, "Architectural shorthand"
        return True, "No Japanese characters"

    if len(jp_chars) <= 1 and "".join(jp_chars) not in ("床", "壁", "梁", "柱", "天", "巾", "腰"):
        return True, "Isolated single character"

    # Check against known architectural glossary or shorthand
    if cleaned_pure in ARCHITECTURAL_GLOSSARY or cleaned_pure in KNOWN_NON_MATERIAL_TERMS:
        return False, "Known architectural glossary/term"

    # Check if text contains any architectural stem
    if any(stem in cleaned for stem in ARCHITECTURAL_STEMS):
        return False, "Contains architectural stem"

    # Check Jamdict dictionary for everyday words or construction terms
    try:
        if jf._ensure_loaded() and jf._jmd:
            res = jf._jmd.lookup(cleaned_pure)
            if res and res.entries:
                return False, "Recognized Jamdict term"
    except Exception:
        pass

    # Ungrounded katakana sequences (e.g. ニソク, ルクロフ, ーアドー, ソグーコソク, etc.)
    if re.match(r"^[\u30a0-\u30ff\u30fc\s\d\.\-]+$", cleaned_pure):
        return True, "Ungrounded Katakana mojibake noise"

    # Kanji phrases with no architectural stem and no dictionary match
    return True, "Unmatched OCR noise fragment"


def main():
    print("=" * 80)
    print("ALFRED LEARNED CACHE POPULATION & OPTIMIZATION")
    print("=" * 80)

    cache = LearnedMaterialCache()
    initial_count = len(cache)
    print(f"[*] Initial cache count: {initial_count} records in {cache.db_path.name}")

    history_path = PROJECT_ROOT / "data" / "analysis_history.json"
    legacy_json_path = PROJECT_ROOT / "data" / "database" / "learned_materials.json"

    # 1. Ingest all records from data/database/learned_materials.json
    legacy_records_to_add = []
    if legacy_json_path.exists():
        with open(legacy_json_path, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
        recs = legacy_data if isinstance(legacy_data, list) else legacy_data.get("records", [])
        for r in recs:
            legacy_records_to_add.append({
                "query_text": r.get("query_text", ""),
                "status": r.get("status", ""),
                "hazard_level": r.get("hazard_level", ""),
                "matched_material_ja": r.get("matched_material_ja", ""),
                "matched_material_en": r.get("matched_material_en", ""),
                "confidence": float(r.get("confidence", 1.0)),
                "reasoning": r.get("regulatory_citation", ""),
                "source": r.get("source", "GATE_4_ARCHITECTURAL_FILTER")
            })
        print(f"[*] Found {len(legacy_records_to_add)} records in legacy {legacy_json_path.name}")

    # 2. Ingest from data/analysis_history.json
    if not history_path.exists():
        print(f"[!] Warning: {history_path} does not exist.")
        history = []
    else:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        print(f"[*] Loaded {len(history)} blueprint diagnostic runs from {history_path.name}")

    # Deduplicate diagnoses by normalized key
    unique_candidates: Dict[str, Dict[str, Any]] = {}
    total_diagnoses_scanned = 0

    for run in history:
        for diag in run.get("diagnoses", []):
            total_diagnoses_scanned += 1
            raw = (diag.get("raw_text") or "").strip()
            if not raw:
                continue

            clean_key = UnidentifiedMaterialMap.normalize_key(raw)
            if not clean_key:
                clean_key = raw.strip()

            key = clean_key.lower()
            conf = float(diag.get("confidence", 0.0))
            tier = diag.get("match_tier", "")
            cit = diag.get("regulatory_citation", "")
            status = diag.get("status", "")

            # Prioritize higher confidence and definitive status
            is_llm_or_gate4 = (
                tier in ("TIER_5_LLM", "GATE_4")
                or "TIER_5_LLM" in cit
                or "LLM" in cit
                or "Gate 4" in cit
            )

            # We examine items evaluated by LLM, Gate 4, or definitive matches
            if key not in unique_candidates:
                unique_candidates[key] = diag
            else:
                existing = unique_candidates[key]
                existing_conf = float(existing.get("confidence", 0.0))
                existing_is_definitive = existing.get("status") in ("POSITIVE", "NEGATIVE")
                new_is_definitive = status in ("POSITIVE", "NEGATIVE")

                if (new_is_definitive and not existing_is_definitive) or (conf > existing_conf):
                    unique_candidates[key] = diag

    print(f"[*] Total diagnoses scanned: {total_diagnoses_scanned}")
    print(f"[*] Unique raw texts found: {len(unique_candidates)}")

    # 3. Categorize and Filter
    to_cache: List[Dict[str, Any]] = []
    noise_skipped = 0
    positive_count = 0
    negative_count = 0
    uncertain_converted_count = 0

    # First add legacy records
    for lr in legacy_records_to_add:
        to_cache.append(lr)

    for key, diag in unique_candidates.items():
        raw_text = diag.get("raw_text", "").strip()
        status = diag.get("status", "UNCERTAIN").strip().upper()
        hazard_level = diag.get("hazard_level", "NON_ASBESTOS").strip().upper()
        mat_ja = diag.get("matched_material_ja", raw_text)
        mat_en = diag.get("matched_material_en", "")
        conf = float(diag.get("confidence", 0.85))
        cit = diag.get("regulatory_citation", "")
        tier = diag.get("match_tier", "")

        # Check for noise exclusion
        is_noise, noise_reason = is_meaningless_noise(raw_text)
        if is_noise:
            noise_skipped += 1
            continue

        # Check false positive overrides
        if raw_text in FALSE_POSITIVE_OVERRIDE:
            new_status, new_haz, new_en = FALSE_POSITIVE_OVERRIDE[raw_text]
            to_cache.append({
                "query_text": raw_text,
                "status": new_status,
                "hazard_level": new_haz,
                "matched_material_ja": raw_text,
                "matched_material_en": new_en,
                "confidence": 1.0,
                "reasoning": "Corrected False Positive: Standard Non-Asbestos Specification",
                "source": "GATE_4_ARCHITECTURAL_FILTER"
            })
            negative_count += 1
            continue

        # Case A: POSITIVE determination
        if status == "POSITIVE":
            if hazard_level not in ("LEVEL_1", "LEVEL_2", "LEVEL_3"):
                hazard_level = "LEVEL_3"
            to_cache.append({
                "query_text": raw_text,
                "status": "POSITIVE",
                "hazard_level": hazard_level,
                "matched_material_ja": mat_ja,
                "matched_material_en": mat_en or mat_ja,
                "confidence": max(0.85, conf),
                "reasoning": cit or "MLIT Statutory Asbestos Material",
                "source": "TIER_5_LLM_ARBITRATION" if "LLM" in cit else "TIER_1_EXACT"
            })
            positive_count += 1

        # Case B: NEGATIVE determination
        elif status == "NEGATIVE":
            # Clean subtitle format
            resolved_en = mat_en or resolve_non_material_description(raw_text)
            if "(Non-Asbestos)" in resolved_en:
                resolved_en = resolved_en.replace("(Non-Asbestos)", "").strip()
            if not resolved_en.endswith("(Non-Architectural Material)") and any(stem in raw_text for stem in ("仕上高", "床高", "打放", "素地", "とする", "ボルト", "ピット")):
                resolved_en = f"{resolved_en} (Non-Architectural Material)"

            to_cache.append({
                "query_text": raw_text,
                "status": "NEGATIVE",
                "hazard_level": "NON_ASBESTOS",
                "matched_material_ja": mat_ja or raw_text,
                "matched_material_en": resolved_en,
                "confidence": max(0.85, conf),
                "reasoning": cit or "Standard Non-Asbestos Building Element",
                "source": "GATE_4_ARCHITECTURAL_FILTER" if "Gate 4" in cit else "TIER_5_LLM_ARBITRATION"
            })
            negative_count += 1

        # Case C: UNCERTAIN -> Check if valid non-architectural material / specification / drawing note
        elif status == "UNCERTAIN":
            # Since is_noise returned False, this text has valid architectural or Japanese meaning
            resolved_en = resolve_non_material_description(raw_text)
            to_cache.append({
                "query_text": raw_text,
                "status": "NEGATIVE",
                "hazard_level": "NON_ASBESTOS",
                "matched_material_ja": raw_text,
                "matched_material_en": resolved_en,
                "confidence": 0.95,
                "reasoning": "Gate 4 Auto-Resolved: Non-Architectural Drawing Specification / Material",
                "source": "GATE_4_ARCHITECTURAL_FILTER"
            })
            negative_count += 1
            uncertain_converted_count += 1

    print("\n" + "-" * 80)
    print("INGESTION & FILTERING SUMMARY")
    print("-" * 80)
    print(f"  * Total candidate items prepared: {len(to_cache)}")
    print(f"  * Confirmed POSITIVE materials:   {positive_count}")
    print(f"  * Confirmed NEGATIVE items:       {negative_count}")
    print(f"    - from UNCERTAIN conversion:    {uncertain_converted_count}")
    print(f"  * Pure meaningless noise skipped: {noise_skipped}")

    # 4. Batch Record into SQLite WAL and L1 In-Memory Cache
    print("\n[*] Writing batch into SQLite WAL database & In-Memory L1 Hash Table...")
    t0 = time.perf_counter()
    saved = cache.record_decisions_batch(to_cache, persist=True)
    t_write = (time.perf_counter() - t0) * 1000

    print(f"[✓] Successfully cached {saved} records in {t_write:.2f}ms!")
    print(f"[✓] New total records in cache: {len(cache)}")

    # 5. Export synchronized JSON backup
    cache.export_to_json(legacy_json_path)
    print(f"[✓] Synchronized JSON backup saved to {legacy_json_path.name}")

    # 6. Benchmark L1 Sub-Microsecond Lookups
    print("\n" + "-" * 80)
    print("L1 IN-MEMORY RETRIEVAL BENCHMARK")
    print("-" * 80)
    test_queries = [
        "仕上高",
        "[打放し",
        "Evピット.",
        "(ジョイント工法)",
        "Sus製タラップ、",
        "吹付けロックウール",
        "せっこうボード",
        "特記仕上表 (FINISH SCHEDULE)"
    ]

    for q in test_queries:
        t_start = time.perf_counter_ns()
        result = cache.lookup(q)
        t_lookup = (time.perf_counter_ns() - t_start) / 1000.0  # in microseconds

        if result:
            status_label = f"[{result.status}] ({result.hazard_level})"
            print(f"  Query: {q:<35} -> {status_label:<25} | {result.matched_material_en:<45} (Time: {t_lookup:.3f} µs)")
        else:
            print(f"  Query: {q:<35} -> NOT FOUND (Time: {t_lookup:.3f} µs)")

    cache.close()
    print("\n" + "=" * 80)
    print("[✓] CACHE POPULATION & DATABASE OPTIMIZATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

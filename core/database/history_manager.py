"""
Persistent Analysis History Database Manager.
Stores, retrieves, and indexes all previously analyzed blueprint files and their diagnosis reports.
Thread-safe and atomic persistence to prevent corruption or race conditions.
"""

from __future__ import annotations
import os
import json
import threading
import datetime
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

HISTORY_FILE = Path("data/analysis_history.json")


class BlueprintHistoryManager:
    """Manages persistent archive of all analyzed blueprints and their inspection reports."""

    def __init__(self, storage_path: Path = HISTORY_FILE):
        self.storage_path = storage_path
        self._lock = threading.Lock()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_records([])

    def _load_records(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.storage_path.exists():
                return []
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history database: {e}. Attempting auto-recovery...")
                try:
                    raw = self.storage_path.read_text(encoding="utf-8")
                    match = re.search(r'\]\s*\{', raw)
                    if match:
                        start, end = match.span()
                        part1 = json.loads(raw[:start + 1])
                        part2_str = "[" + raw[end - 1:]
                        if not part2_str.strip().endswith("]"):
                            part2_str = part2_str.rstrip() + "\n]"
                        part2 = json.loads(part2_str)
                        recovered = part1 + part2
                        temp_path = self.storage_path.with_suffix(".tmp")
                        with open(temp_path, "w", encoding="utf-8") as tf:
                            json.dump(recovered, tf, ensure_ascii=False, indent=2)
                        os.replace(str(temp_path), str(self.storage_path))
                        print(f"Auto-recovery successful: restored {len(recovered)} records")
                        return recovered
                except Exception as rec_err:
                    print(f"Auto-recovery failed: {rec_err}")
                return []

    def _save_records(self, records: List[Dict[str, Any]]) -> None:
        with self._lock:
            try:
                temp_path = self.storage_path.with_suffix(".tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                os.replace(str(temp_path), str(self.storage_path))
            except Exception as e:
                print(f"Error saving history database: {e}")

    def get_all(self, include_full: bool = False) -> List[Dict[str, Any]]:
        """Returns all previously analyzed blueprint records sorted by timestamp descending.
        By default excludes large image payloads for fast listing.
        """
        records = self._load_records()
        sorted_records = sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)
        if include_full:
            return sorted_records
        
        summaries = []
        for r in sorted_records:
            summaries.append({
                "drawing_id": r.get("drawing_id"),
                "filename": r.get("filename"),
                "timestamp": r.get("timestamp"),
                "document_type": r.get("document_type"),
                "is_vector_pdf": r.get("is_vector_pdf"),
                "page_count": r.get("page_count", 1),
                "overall_verdict": r.get("overall_verdict"),
                "verdict_label": r.get("verdict_label"),
                "total_material_annotations": r.get("total_material_annotations", 0),
                "processing_time_seconds": r.get("processing_time_seconds"),
                "summary": r.get("summary", {}),
                "positive_materials": r.get("positive_materials", []),
                "quality_assessment": r.get("quality_assessment"),
                "has_preview": bool(r.get("image_base64") or r.get("thumbnail_base64"))
            })
        return summaries

    def get_by_id(self, drawing_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete diagnosis report for a specific drawing ID."""
        records = self._load_records()
        for r in records:
            if r.get("drawing_id") == drawing_id:
                return r
        return None

    def record_analysis(
        self,
        drawing_id: str,
        filename: str,
        document_type: str,
        is_vector_pdf: bool,
        page_count: int,
        summary: Dict[str, Any],
        diagnoses: List[Dict[str, Any]],
        finish_schedule: List[Dict[str, Any]],
        room_assessments: Optional[List[Dict[str, Any]]] = None,
        image_base64: Optional[str] = None,
        image_width: int = 2400,
        image_height: int = 1600,
        table_bbox: Optional[List[float]] = None,
        quality_assessment: Optional[Dict[str, Any]] = None,
        processing_time_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Saves or updates an analyzed blueprint into the persistent database."""
        records = self._load_records()

        # Extract unique detected positive materials
        pos_materials = []
        for d in diagnoses:
            if d.get("status") == "POSITIVE":
                mat = d.get("matched_material_ja", "")
                if mat and mat not in pos_materials:
                    pos_materials.append(mat)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determine overall safety determination
        pos_count = summary.get("asbestos_positive", 0)
        if pos_count > 0:
            overall_verdict = "HAZARDOUS_ASBESTOS_DETECTED"
            verdict_label = f"POSITIVE ({pos_count} hazardous materials)"
        elif summary.get("uncertain", 0) > 0 or summary.get("review_required", 0) > 0:
            overall_verdict = "REQUIRES_VERIFICATION"
            verdict_label = "REVIEW REQUIRED"
        else:
            overall_verdict = "CERTIFIED_NON_ASBESTOS"
            verdict_label = "CERTIFIED SAFE"

        record = {
            "drawing_id": drawing_id,
            "filename": filename,
            "timestamp": now,
            "document_type": document_type,
            "is_vector_pdf": is_vector_pdf,
            "page_count": page_count,
            "image_width": image_width,
            "image_height": image_height,
            "table_bbox": table_bbox,
            "quality_assessment": quality_assessment,
            "processing_time_seconds": processing_time_seconds,
            "overall_verdict": overall_verdict,
            "verdict_label": verdict_label,
            "total_material_annotations": len(diagnoses),
            "summary": summary,
            "positive_materials": pos_materials,
            "diagnoses": diagnoses,
            "finish_schedule": finish_schedule,
            "room_assessments": room_assessments or [],
            "thumbnail_base64": "",
            "image_base64": ""
        }

        # Upsert: Replace if existing, or prepend
        existing_idx = next((i for i, r in enumerate(records) if r.get("drawing_id") == drawing_id), None)
        if existing_idx is not None:
            records[existing_idx] = record
        else:
            records.insert(0, record)

        self._save_records(records)
        return record

    def delete(self, drawing_id: str) -> bool:
        """Deletes a record from history database."""
        records = self._load_records()
        initial_len = len(records)
        records = [r for r in records if r.get("drawing_id") != drawing_id]
        if len(records) != initial_len:
            self._save_records(records)
            return True
        return False

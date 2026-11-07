"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Send,
  Sparkles,
  Info,
  Check,
  Copy,
  BookOpen,
  Cpu,
} from "lucide-react";
import {
  DiagnosisItem,
  AsbestosStatus,
  HazardLevel,
  HumanOverridePayload,
  QualityAssessment,
} from "@/types/drawing";

interface InspectorPanelProps {
  drawingId: string;
  diagnoses: DiagnosisItem[];
  selectedItem: DiagnosisItem | null;
  onSelectItem: (item: DiagnosisItem) => void;
  onOverrideSuccess: (updatedItem: DiagnosisItem) => void;
  onSubmitOverride: (payload: HumanOverridePayload) => Promise<any>;
  qualityAssessment?: QualityAssessment | null;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  drawingId,
  diagnoses,
  selectedItem,
  onSelectItem,
  onOverrideSuccess,
  onSubmitOverride,
  qualityAssessment,
}) => {
  // Override form state
  const [overrideStatus, setOverrideStatus] = useState<AsbestosStatus>("POSITIVE");
  const [overrideHazard, setOverrideHazard] = useState<HazardLevel>("LEVEL_1");
  const [overrideMaterial, setOverrideMaterial] = useState<string>("");
  const [reviewerNotes, setReviewerNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitFeedback, setSubmitFeedback] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Sync form when selected item changes
  useEffect(() => {
    if (selectedItem) {
      setOverrideStatus(selectedItem.status);
      setOverrideHazard(selectedItem.hazard_level);
      setOverrideMaterial(selectedItem.matched_material_ja);
      setReviewerNotes("");
      setSubmitFeedback(null);
    }
  }, [selectedItem]);

  if (!selectedItem) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 h-full flex flex-col items-center justify-center text-center text-slate-500">
        <Info className="w-10 h-10 mb-3 text-slate-600" />
        <h4 className="text-sm font-semibold text-slate-300">No Item Selected</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          Click on any bounding box on the blueprint canvas or select an entity from the inspection table to view diagnostics and active learning overrides.
        </p>
      </div>
    );
  }

  const currentIndex = diagnoses.findIndex((d) => d.item_id === selectedItem.item_id);

  const handlePrev = () => {
    if (currentIndex > 0) {
      onSelectItem(diagnoses[currentIndex - 1]);
    }
  };

  const handleNext = () => {
    if (currentIndex < diagnoses.length - 1) {
      onSelectItem(diagnoses[currentIndex + 1]);
    }
  };

  const handleCopyRaw = () => {
    navigator.clipboard.writeText(selectedItem.raw_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitFeedback(null);

    try {
      const payload: HumanOverridePayload = {
        item_id: selectedItem.item_id,
        drawing_id: drawingId,
        corrected_status: overrideStatus,
        corrected_hazard_level: overrideHazard,
        corrected_material_name: overrideMaterial,
        reviewer_notes: reviewerNotes,
      };

      await onSubmitOverride(payload);

      // Locally update item
      const updated: DiagnosisItem = {
        ...selectedItem,
        status: overrideStatus,
        hazard_level: overrideHazard,
        matched_material_ja: overrideMaterial,
        requires_human_review: false,
      };
      onOverrideSuccess(updated);

      setSubmitFeedback("Human verification saved into active learning pool!");
      setTimeout(() => setSubmitFeedback(null), 4000);
    } catch (err: any) {
      setSubmitFeedback(`Error: ${err.message || "Failed to submit"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Status visual attributes
  const isPositive = selectedItem.status === "POSITIVE";
  const isNegative = selectedItem.status === "NEGATIVE";
  const isUncertain = selectedItem.status === "UNCERTAIN";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl flex flex-col h-full overflow-hidden shadow-2xl">
      {/* Header & Quick Navigation */}
      <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-600 text-white">
            #{currentIndex + 1}
          </span>
          <span className="font-mono text-xs text-slate-400">
            {selectedItem.item_id}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handlePrev}
            disabled={currentIndex <= 0}
            className="p-1 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition"
            title="Previous item"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono text-slate-400 px-1">
            {currentIndex + 1} / {diagnoses.length}
          </span>
          <button
            onClick={handleNext}
            disabled={currentIndex >= diagnoses.length - 1}
            className="p-1 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition"
            title="Next item"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Status & Hazard Banner */}
        <div
          className={`p-3.5 rounded-xl border ${isPositive
              ? "bg-rose-950/40 border-rose-600/60 text-rose-200"
              : isNegative
                ? "bg-emerald-950/40 border-emerald-600/60 text-emerald-200"
                : "bg-amber-950/40 border-amber-600/60 text-amber-200"
            }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isPositive && <ShieldAlert className="w-5 h-5 text-rose-400" />}
              {isNegative && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
              {isUncertain && <AlertTriangle className="w-5 h-5 text-amber-400" />}
              <span className="font-bold text-sm">
                {selectedItem.status} [{selectedItem.hazard_level}]
              </span>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-black/40 font-semibold">
              {(selectedItem.confidence * 100).toFixed(1)}% Match
            </span>
          </div>

          <p className="text-xs mt-2 text-slate-300">
            {selectedItem.matched_material_ja}{" "}
            <span className="text-slate-400">({selectedItem.matched_material_en})</span>
          </p>
        </div>

        {/* OCR & Normalized Text */}
        <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 space-y-2">
          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span>Raw OCR Text (生OCR)</span>
              <button
                onClick={handleCopyRaw}
                className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-blue-400 transition"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800/80 font-mono text-xs text-slate-200 break-all select-all">
              {selectedItem.raw_text}
            </div>
          </div>

          <div>
            <div className="text-[11px] text-slate-400 mb-1">
              NFKC Normalized (全角半角正規化)
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800/80 font-mono text-xs text-blue-300 break-all">
              {selectedItem.normalized_text}
            </div>
          </div>
        </div>

        {/* Match Tier & Regulatory Citations */}
        <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 space-y-2 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-slate-400">Matching Tier:</span>
            <span className="font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-semibold text-[11px]">
              {selectedItem.match_tier}
            </span>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-slate-400">Layout Region:</span>
            <span className="font-mono text-slate-300 text-[11px]">
              {selectedItem.region_type}
            </span>
          </div>

          {selectedItem.room_context && (
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="text-slate-400">Room Context:</span>
              <span className="text-slate-200 font-medium">
                {selectedItem.room_context}
              </span>
            </div>
          )}

          <div className="pt-1">
            <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1 mb-1">
              <BookOpen className="w-3.5 h-3.5 text-blue-400" />
              MLIT Regulatory Citation:
            </span>
            <p className="text-[11px] text-slate-300 leading-relaxed bg-slate-900/90 p-2 rounded border border-slate-800/60">
              {selectedItem.regulatory_citation}
            </p>
          </div>
        </div>

        {/* Adaptive Preprocessing Brain Details */}
        {qualityAssessment && (
          <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 space-y-2 text-xs">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                Adaptive Vision Decision
              </span>
              <span
                className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                  qualityAssessment.intensity_level === 0
                    ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                    : qualityAssessment.intensity_level === 1
                    ? "bg-cyan-950 text-cyan-300 border border-cyan-700"
                    : "bg-amber-950 text-amber-300 border border-amber-700"
                }`}
              >
                {qualityAssessment.intensity_level === 0
                  ? "Level 0 • Pass-Through"
                  : qualityAssessment.intensity_level === 1
                  ? "Level 1 • Gentle Deskew"
                  : "Level 2 • Deep Restoration"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-tight">
              {qualityAssessment.recommendation_reason}
            </p>
            <div className="grid grid-cols-2 gap-1.5 pt-1 text-[10px] font-mono text-slate-400">
              <div className="p-1.5 rounded bg-slate-900 border border-slate-800/80">
                Noise Sigma: <span className="text-white font-bold">{qualityAssessment.noise_sigma}</span>
              </div>
              <div className="p-1.5 rounded bg-slate-900 border border-slate-800/80">
                Skew Angle: <span className="text-white font-bold">{qualityAssessment.skew_angle}°</span>
              </div>
            </div>
          </div>
        )}

        {/* Human-in-the-Loop Active Learning Form */}
        <div className="bg-slate-950/80 rounded-xl p-3.5 border border-slate-800">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200 mb-3">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Human-in-the-Loop Verification</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3 text-xs">
            {/* Status Select */}
            <div>
              <label className="block text-slate-400 mb-1 text-[11px]">
                Verify Asbestos Status:
              </label>
              <select
                value={overrideStatus}
                onChange={(e) => setOverrideStatus(e.target.value as AsbestosStatus)}
                className="w-full bg-slate-900 text-slate-200 border border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 font-medium"
              >
                <option value="POSITIVE">POSITIVE (石綿陽性)</option>
                <option value="NEGATIVE">NEGATIVE (非石綿・安全)</option>
                <option value="UNCERTAIN">UNCERTAIN (要確認・保留)</option>
              </select>
            </div>

            {/* Hazard Select */}
            <div>
              <label className="block text-slate-400 mb-1 text-[11px]">
                Hazard Level (MLIT Classification):
              </label>
              <select
                value={overrideHazard}
                onChange={(e) => setOverrideHazard(e.target.value as HazardLevel)}
                className="w-full bg-slate-900 text-slate-200 border border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 font-medium"
              >
                <option value="LEVEL_1">LEVEL 1 (吹付け石綿・著しく飛散)</option>
                <option value="LEVEL_2">LEVEL 2 (保温材・耐火被覆・飛散)</option>
                <option value="LEVEL_3">LEVEL 3 (成形板・飛散しにくい)</option>
                <option value="NON_ASBESTOS">NON_ASBESTOS (適合・安全)</option>
                <option value="UNCERTAIN">UNCERTAIN (判定保留)</option>
              </select>
            </div>

            {/* Reviewer Notes */}
            <div>
              <label className="block text-slate-400 mb-1 text-[11px]">
                Reviewer Notes (Lab verification details):
              </label>
              <input
                type="text"
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="e.g. PLM microscopy confirmed Chrysotile 12%"
                className="w-full bg-slate-900 text-slate-200 border border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 text-xs"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-2 px-3 rounded-lg transition shadow-lg shadow-blue-600/20 active:scale-98 disabled:opacity-50 text-xs"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isSubmitting ? "Saving..." : "Save Human Verification"}</span>
            </button>

            {submitFeedback && (
              <div
                className={`p-2 rounded text-[11px] font-medium text-center ${submitFeedback.startsWith("Error")
                    ? "bg-rose-950 text-rose-300 border border-rose-800"
                    : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                  }`}
              >
                {submitFeedback}
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

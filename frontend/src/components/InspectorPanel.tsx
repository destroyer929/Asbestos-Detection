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
      <div className="bg-white border border-emerald-200 rounded-2xl p-6 h-full flex flex-col items-center justify-center text-center text-slate-500 shadow-sm">
        <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 mb-3">
          <Info className="w-8 h-8" />
        </div>
        <h4 className="text-sm font-bold text-slate-800 tracking-wide">No Material Selected</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs font-sans">
          Click on any bounding box on the blueprint canvas or select an entity from the inspection table to review diagnostics and verify regulatory status.
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

      setSubmitFeedback("Verified & saved into Alfred Active Learning pool!");
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
    <div className="bg-white border-2 border-emerald-300 rounded-2xl flex flex-col h-full overflow-hidden shadow-md shadow-emerald-950/5">
      {/* Header & Quick Navigation */}
      <div className="bg-emerald-50/80 px-4 py-3 border-b-2 border-emerald-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-lab-mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-600 text-white shadow-2xs">
            #{currentIndex + 1}
          </span>
          <span className="font-lab-mono text-xs text-slate-800 font-bold truncate max-w-[140px]">
            {selectedItem.item_id}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handlePrev}
            disabled={currentIndex <= 0}
            className="p-1.5 rounded-full bg-white text-slate-700 hover:text-emerald-800 disabled:opacity-30 disabled:pointer-events-none transition border border-slate-200 shadow-2xs"
            title="Previous item"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs font-lab-mono text-slate-600 px-1 font-bold">
            {currentIndex + 1} / {diagnoses.length}
          </span>
          <button
            onClick={handleNext}
            disabled={currentIndex >= diagnoses.length - 1}
            className="p-1.5 rounded-full bg-white text-slate-700 hover:text-emerald-800 disabled:opacity-30 disabled:pointer-events-none transition border border-slate-200 shadow-2xs"
            title="Next item"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {/* Status & Hazard Banner */}
        <div
          className={`p-3.5 rounded-2xl border ${
            isPositive
              ? "bg-rose-50 border-2 border-rose-300 text-rose-800 shadow-2xs"
              : isNegative
              ? "bg-emerald-50 border-2 border-emerald-400 text-emerald-800 shadow-2xs"
              : "bg-amber-50 border-2 border-amber-300 text-amber-800 shadow-2xs"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isPositive && <ShieldAlert className="w-5 h-5 text-rose-600 flex-shrink-0" />}
              {isNegative && <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />}
              {isUncertain && <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />}
              <span className="font-extrabold text-sm tracking-tight">
                {selectedItem.status} [{selectedItem.hazard_level}]
              </span>
            </div>
            <span className="text-xs font-lab-mono px-2.5 py-0.5 rounded-full bg-white font-bold border border-slate-200 shadow-2xs">
              {(selectedItem.confidence * 100).toFixed(1)}% Match
            </span>
          </div>

          <p className="text-xs mt-2 text-slate-800 font-bold">
            {selectedItem.matched_material_ja}{" "}
            <span className="text-slate-500 font-normal">({selectedItem.matched_material_en})</span>
          </p>
        </div>

        {/* OCR & Normalized Text */}
        <div className="bg-emerald-50/60 rounded-2xl p-3.5 border-2 border-emerald-200 space-y-2.5">
          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-600 mb-1">
              <span className="font-bold">Raw OCR Text (生OCR)</span>
              <button
                onClick={handleCopyRaw}
                className="flex items-center gap-1 text-[10px] text-emerald-700 hover:text-emerald-900 transition font-bold"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <div className="p-2.5 rounded-xl bg-white border border-emerald-200 font-lab-mono text-xs text-slate-900 break-all select-all shadow-2xs">
              {selectedItem.raw_text}
            </div>
          </div>

          <div>
            <div className="text-[11px] text-slate-600 mb-1 font-bold">
              NFKC Normalized (全角半角正規化)
            </div>
            <div className="p-2.5 rounded-xl bg-white border border-emerald-200 font-lab-mono text-xs text-emerald-800 break-all shadow-2xs">
              {selectedItem.normalized_text}
            </div>
          </div>
        </div>

        {/* Match Tier & Regulatory Citations */}
        <div className="bg-slate-50/80 rounded-2xl p-3.5 border-2 border-slate-200 space-y-2 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200/80">
            <span className="text-slate-600 font-medium">Matching Tier:</span>
            {selectedItem.match_tier === "TIER_5_LLM" ? (
              <span className="font-lab-mono px-2.5 py-0.5 rounded-full bg-purple-100 border border-purple-300 text-purple-900 font-bold text-[11px] inline-flex items-center gap-1 shadow-2xs">
                <span>🤖</span> T5_LLM
              </span>
            ) : selectedItem.match_tier === "GATE_4" ? (
              <span className="font-lab-mono px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-800 border border-slate-300 font-bold text-[11px]">
                GATE_4 (Pre-LLM Filter)
              </span>
            ) : (
              <span className="font-lab-mono px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 font-bold text-[11px]">
                {selectedItem.match_tier}
              </span>
            )}
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-200/80">
            <span className="text-slate-600 font-medium">Layout Region:</span>
            <span className="font-lab-mono text-slate-800 font-bold text-[11px]">
              {selectedItem.region_type}
            </span>
          </div>

          {selectedItem.room_context && (
            <div className="flex items-center justify-between pb-2 border-b border-slate-200/80">
              <span className="text-slate-600 font-medium">Room Context:</span>
              <span className="text-slate-900 font-bold">
                {selectedItem.room_context}
              </span>
            </div>
          )}

          <div className="pt-1">
            <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
              <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
              <span>MLIT Regulatory Citation:</span>
            </span>
            <p className="text-[11px] text-slate-700 leading-relaxed bg-white p-2.5 rounded-xl border border-slate-200 font-sans shadow-2xs">
              {selectedItem.regulatory_citation}
            </p>
          </div>
        </div>

        {/* Adaptive Preprocessing Vision Details */}
        {qualityAssessment && (
          <div className="bg-slate-50/80 rounded-2xl p-3.5 border-2 border-slate-200 space-y-2 text-xs">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-200/80">
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                Adaptive Vision Decision
              </span>
              <span
                className={`font-lab-mono text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  qualityAssessment.intensity_level === 0
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : qualityAssessment.intensity_level === 1
                    ? "bg-teal-100 text-teal-800 border border-teal-300"
                    : "bg-amber-100 text-amber-800 border border-amber-300"
                }`}
              >
                {qualityAssessment.intensity_level === 0
                  ? "Level 0 • Pass-Through"
                  : qualityAssessment.intensity_level === 1
                  ? "Level 1 • Gentle Deskew"
                  : "Level 2 • Deep Restoration"}
              </span>
            </div>
            <p className="text-[11px] text-slate-600 leading-tight">
              {qualityAssessment.recommendation_reason}
            </p>
            <div className="grid grid-cols-2 gap-1.5 pt-1 text-[10px] font-lab-mono text-slate-600">
              <div className="p-1.5 rounded-lg bg-white border border-slate-200">
                Noise Sigma: <span className="text-slate-900 font-bold">{qualityAssessment.noise_sigma}</span>
              </div>
              <div className="p-1.5 rounded-lg bg-white border border-slate-200">
                Skew Angle: <span className="text-slate-900 font-bold">{qualityAssessment.skew_angle}°</span>
              </div>
            </div>
          </div>
        )}

        {/* Human-in-the-Loop Active Learning Form */}
        <div className="bg-emerald-50/60 rounded-2xl p-4 border-2 border-emerald-200">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 mb-3">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Human-in-the-Loop Verification</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3 text-xs">
            {/* Status Select */}
            <div>
              <label className="block text-slate-700 mb-1 text-[11px] font-bold">
                Verify Asbestos Status:
              </label>
              <select
                value={overrideStatus}
                onChange={(e) => setOverrideStatus(e.target.value as AsbestosStatus)}
                className="w-full bg-white text-slate-900 border border-emerald-200 rounded-xl p-2.5 focus:ring-1 focus:ring-emerald-500 font-medium shadow-2xs"
              >
                <option value="POSITIVE">POSITIVE (石綿陽性)</option>
                <option value="NEGATIVE">NEGATIVE (非石綿・安全)</option>
                <option value="UNCERTAIN">UNCERTAIN (要確認・保留)</option>
              </select>
            </div>

            {/* Hazard Select */}
            <div>
              <label className="block text-slate-700 mb-1 text-[11px] font-bold">
                Hazard Level (MLIT Classification):
              </label>
              <select
                value={overrideHazard}
                onChange={(e) => setOverrideHazard(e.target.value as HazardLevel)}
                className="w-full bg-white text-slate-900 border border-emerald-200 rounded-xl p-2.5 focus:ring-1 focus:ring-emerald-500 font-medium shadow-2xs"
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
              <label className="block text-slate-700 mb-1 text-[11px] font-bold">
                Reviewer Notes (Lab verification details):
              </label>
              <input
                type="text"
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="e.g. PLM microscopy confirmed Chrysotile 12%"
                className="w-full bg-white text-slate-900 border border-emerald-200 rounded-xl p-2.5 focus:ring-1 focus:ring-emerald-500 text-xs placeholder:text-slate-400 shadow-2xs"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-hover-shine w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white font-bold py-2.5 px-4 rounded-full transition shadow-md shadow-emerald-600/20 active:scale-98 disabled:opacity-50 text-xs"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isSubmitting ? "Saving..." : "Save Human Verification"}</span>
            </button>

            {submitFeedback && (
              <div
                className={`p-2.5 rounded-xl text-[11px] font-bold text-center ${
                  submitFeedback.startsWith("Error")
                    ? "bg-rose-50 text-rose-800 border border-rose-300"
                    : "bg-emerald-50 text-emerald-800 border border-emerald-300"
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

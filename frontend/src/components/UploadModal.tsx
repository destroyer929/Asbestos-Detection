"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import {
  X,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  Cpu,
} from "lucide-react";
import { DrawingAnalysisResponse } from "@/types/drawing";
import {
  analyzeUploadedFile,
  fetchAnalysisProgress,
  AnalysisProgressInfo,
} from "@/lib/api";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (data: DrawingAnalysisResponse) => void;
}

// ─── Pipeline analysis stages ───────────────────────────────────────────────
const ANALYSIS_STAGES = [
  { id: "ingest",     minPct: 0,  maxPct: 15, label: "Ingesting blueprint file",        sublabel: "PDF / image router • multi-page detection" },
  { id: "preprocess", minPct: 15, maxPct: 35, label: "Adaptive preprocessing",          sublabel: "Sauvola binarization • line separation • deskew" },
  { id: "ocr",        minPct: 35, maxPct: 65, label: "PaddleOCR CJK Text Extraction",   sublabel: "Multi-scale text detection • Japanese recognition" },
  { id: "layout",     minPct: 65, maxPct: 80, label: "Layout & table analysis",         sublabel: "Finish Schedule detection • cell segmentation" },
  { id: "match",      minPct: 80, maxPct: 90, label: "4-Tier MLIT regulatory matching", sublabel: "Exact → rule → fuzzy → semantic MLIT verification" },
  { id: "finalize",   minPct: 90, maxPct: 100,label: "Tier-5 LLM Arbitration & Safety", sublabel: "Hazard classification • review queue compilation" },
];

// ─── ProgressModal with Live Tier-5 Feedback ─────────────────────────────────
const ProgressModal: React.FC<{
  filename: string;
  isComplete: boolean;
  progressInfo: AnalysisProgressInfo | null;
}> = ({ filename, isComplete, progressInfo }) => {
  const [estimatedPercent, setEstimatedPercent] = useState<number>(5);

  // Smooth client-side timer fallback if network polling is between ticks
  useEffect(() => {
    if (isComplete) {
      setEstimatedPercent(100);
      return;
    }

    const timer = setInterval(() => {
      setEstimatedPercent((curr) => {
        if (curr >= 92) return curr;
        const inc = curr < 20 ? 1.4 : curr < 50 ? 0.9 : curr < 75 ? 0.6 : 0.25;
        return Math.min(Math.round((curr + inc) * 10) / 10, 92);
      });
    }, 140);

    return () => clearInterval(timer);
  }, [isComplete]);

  // Use authoritative live backend progress if available, otherwise fallback to smooth estimator
  const currentPercent = isComplete
    ? 100
    : progressInfo && typeof progressInfo.percent === "number"
    ? Math.max(progressInfo.percent, estimatedPercent)
    : estimatedPercent;

  const displayPercent = Math.min(100, Math.round(currentPercent));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-md animate-fadeIn">
      <div className="bg-white border-2 border-emerald-300 rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-emerald-50/80 border-b border-emerald-200 flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-white text-emerald-700 flex-shrink-0 border border-emerald-300 shadow-xs">
            {isComplete ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
            )}
          </div>
          <div className="overflow-hidden flex-1">
            <h3 className="font-extrabold text-sm text-slate-900 tracking-wide flex items-center gap-2">
              <span>{isComplete ? "Analysis Complete!" : "Analyzing Blueprint with PaddleOCR…"}</span>
              {!isComplete && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Live Engine
                </span>
              )}
            </h3>
            <p className="text-[11px] text-emerald-800 font-lab-mono truncate mt-0.5">{filename}</p>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Overall Diagnostic Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-900">Overall Diagnostic Progress</span>
              <span className="font-lab-mono font-extrabold text-emerald-700 text-sm">
                {displayPercent}%
              </span>
            </div>
            <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200">
              <div
                className="h-full bg-gradient-to-r from-[#28a745] to-[#20923d] rounded-full transition-all duration-300 ease-out shadow-xs shadow-emerald-500/50"
                style={{ width: `${displayPercent}%` }}
              />
            </div>
            {progressInfo?.message && (
              <p className="text-[11px] font-lab-mono text-emerald-800 font-medium truncate pt-0.5">
                • {progressInfo.message}
              </p>
            )}
          </div>

          {/* Sequential Stages List */}
          <div className="space-y-2">
            {ANALYSIS_STAGES.map((stage) => {
              const isStageDone = isComplete || displayPercent >= stage.maxPct;
              const isStageActive =
                !isComplete && displayPercent >= stage.minPct && displayPercent < stage.maxPct;
              const isTier5 = stage.id === "finalize";

              return (
                <div
                  key={stage.id}
                  className={`flex flex-col p-3 rounded-2xl transition-all duration-200 border ${
                    isStageActive
                      ? "bg-emerald-50/90 border-2 border-emerald-400 shadow-sm"
                      : isStageDone
                      ? "bg-emerald-50/30 border border-emerald-200/90 text-emerald-900"
                      : "border-slate-200/60 opacity-45 bg-slate-50/60 text-slate-400"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {isStageDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : isStageActive ? (
                        <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p
                          className={`text-xs font-bold truncate ${
                            isStageActive
                              ? "text-slate-900"
                              : isStageDone
                              ? "text-emerald-900"
                              : "text-slate-400"
                          }`}
                        >
                          {stage.label}
                        </p>
                        {isTier5 && isStageActive && (
                          <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-900 border border-purple-300">
                            <Cpu className="w-3 h-3 text-purple-600 animate-pulse" />
                            <span>Qwen LLM</span>
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-500 mt-0.5 truncate font-sans">
                        {stage.sublabel}
                      </p>
                    </div>
                  </div>

                  {/* ─── LIVE TIER-5 PROGRESS WIDGET ─── */}
                  {isTier5 && (isStageActive || (isStageDone && progressInfo?.tier5_total !== undefined)) && (
                    <div className="mt-2.5 pt-2.5 border-t border-emerald-200/70 bg-white/80 p-2.5 rounded-xl border border-emerald-200/60 shadow-2xs space-y-2">
                      {progressInfo && progressInfo.tier5_total > 0 ? (
                        <>
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-800 flex items-center gap-1.5">
                              {!isComplete && (
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                              )}
                              <span>Materials Sent to Tier-5:</span>
                            </span>
                            <span className="font-lab-mono font-extrabold text-emerald-900 bg-emerald-100/90 px-2.5 py-0.5 rounded-full border border-emerald-300 shadow-2xs">
                              {progressInfo.tier5_completed} / {progressInfo.tier5_total} completed (
                              {Math.round(
                                (progressInfo.tier5_completed / progressInfo.tier5_total) * 100
                              )}
                              %)
                            </span>
                          </div>

                          {/* Tier-5 Specific Mini Progress Bar */}
                          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200">
                            <div
                              className="h-full bg-gradient-to-r from-emerald-500 to-[#28a745] rounded-full transition-all duration-300 ease-out"
                              style={{
                                width: `${Math.max(
                                  5,
                                  Math.min(
                                    100,
                                    (progressInfo.tier5_completed / progressInfo.tier5_total) * 100
                                  )
                                )}%`,
                              }}
                            />
                          </div>

                          {/* Currently Arbitrated Material Indicator */}
                          {progressInfo.current_material && !isComplete && (
                            <div className="flex items-center gap-1.5 text-[11px] text-slate-700 font-lab-mono truncate">
                              <span className="text-emerald-700 font-bold flex-shrink-0">
                                Current Material:
                              </span>
                              <span className="truncate bg-white px-2 py-0.5 rounded-md border border-emerald-300 text-slate-900 font-bold shadow-2xs">
                                {progressInfo.current_material}
                              </span>
                            </div>
                          )}

                          {isComplete && (
                            <p className="text-[11px] text-emerald-800 font-bold font-lab-mono flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                              <span>All {progressInfo.tier5_total} candidate materials arbitrated!</span>
                            </p>
                          )}
                        </>
                      ) : progressInfo && progressInfo.tier5_total === 0 ? (
                        <div className="flex items-center gap-1.5 text-[11px] text-emerald-800 font-lab-mono font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                          <span>
                            0 items required Tier-5 LLM (100% resolved in 4-Tier MLIT matching)
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between text-xs text-slate-600 font-lab-mono">
                          <span className="flex items-center gap-1.5">
                            <Loader2 className="w-3 h-3 text-emerald-600 animate-spin" />
                            Evaluating candidate queue for Tier-5 LLM...
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <p className="text-center text-[11px] text-slate-500 font-lab-mono">
            Drawscan High-Precision Pipeline • MLIT JIS A 1481 Analysis
          </p>
        </div>
      </div>
    </div>
  );
};

// ─── Main UploadModal Component (Cleaned & Focused) ──────────────────────────
export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [progressInfo, setProgressInfo] = useState<AnalysisProgressInfo | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    const validExts = ["pdf", "png", "jpg", "jpeg", "dxf"];
    if (!ext || !validExts.includes(ext)) {
      setErrorMessage("Please upload a valid blueprint file (.pdf, .png, .jpg, .dxf)");
      return;
    }
    setErrorMessage(null);
    setSelectedFile(file);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;
    const sessionId = `upload_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    setProgressInfo(null);
    setIsUploading(true);
    setIsComplete(false);
    setErrorMessage(null);

    // Poll live progress from backend every 250ms
    const pollInterval = setInterval(async () => {
      try {
        const info = await fetchAnalysisProgress(sessionId);
        if (info) {
          setProgressInfo(info);
          if (info.is_complete) {
            clearInterval(pollInterval);
          }
        }
      } catch {
        // Ignore transient poll failures
      }
    }, 250);

    try {
      const result = await analyzeUploadedFile(selectedFile, sessionId);
      clearInterval(pollInterval);
      setIsComplete(true);
      setTimeout(() => {
        setIsUploading(false);
        setIsComplete(false);
        onUploadSuccess(result);
        onClose();
      }, 550);
    } catch (err: any) {
      clearInterval(pollInterval);
      setIsUploading(false);
      setIsComplete(false);
      setErrorMessage(err.message || "Failed to analyze document.");
    }
  };

  if (isUploading && selectedFile) {
    return (
      <ProgressModal
        filename={selectedFile.name}
        isComplete={isComplete}
        progressInfo={progressInfo}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white border-2 border-emerald-300 rounded-3xl w-full max-w-xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-emerald-50/80 border-b border-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white border-2 border-emerald-200 flex items-center justify-center shadow-xs">
              <Image
                src="/brand/drawscan-logo.png"
                alt="Drawscan Logo"
                width={26}
                height={26}
                className="object-contain"
              />
            </div>
            <div>
              <h3 className="font-extrabold text-base text-slate-900 tracking-wide">
                Upload & Diagnose Architectural Blueprint
              </h3>
              <p className="text-xs text-slate-600 font-sans">
                Vector CAD PDF, High-Res Scanned Blueprint, or DXF
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition disabled:opacity-40"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Upload Body */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.dxf"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Drag & Drop Box */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-emerald-400 hover:border-emerald-600 rounded-3xl p-8 text-center cursor-pointer transition bg-emerald-50/30 hover:bg-emerald-50/60 group shadow-2xs"
          >
            <Upload className="w-10 h-10 mx-auto mb-3 text-emerald-600 group-hover:scale-105 transition" />
            <p className="text-sm font-bold text-slate-900">
              Drag and drop blueprint here, or{" "}
              <span className="text-[#28a745] underline decoration-emerald-500 font-extrabold">
                browse files
              </span>
            </p>
            <p className="text-xs text-slate-500 mt-1.5 font-lab-mono">
              Supports: PDF (Scanned / Vector CAD), JPG, PNG, DXF
            </p>
          </div>

          {selectedFile && (
            <div className="p-4 bg-emerald-50 rounded-2xl border-2 border-emerald-300 flex items-center justify-between shadow-xs">
              <div className="flex items-center gap-3 overflow-hidden">
                <FileText className="w-6 h-6 text-emerald-700 flex-shrink-0" />
                <div className="overflow-hidden">
                  <p className="text-xs font-extrabold text-slate-900 truncate font-lab-mono">
                    {selectedFile.name}
                  </p>
                  <p className="text-[11px] text-slate-600 font-lab-mono mt-0.5">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            </div>
          )}

          {errorMessage && (
            <div className="p-3.5 rounded-2xl bg-rose-50 border-2 border-rose-300 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span className="font-medium">{errorMessage}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-emerald-50/50 border-t border-emerald-200 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="px-5 py-2.5 rounded-full bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition disabled:opacity-40 border border-slate-300 shadow-2xs"
          >
            Cancel
          </button>
          <button
            onClick={handleAnalyze}
            disabled={!selectedFile || isUploading}
            className="btn-hover-shine px-6 py-2.5 rounded-full bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white text-xs font-bold transition shadow-md shadow-emerald-500/20 disabled:opacity-40 disabled:pointer-events-none flex items-center gap-2"
          >
            <span>Diagnose Blueprint</span>
          </button>
        </div>
      </div>
    </div>
  );
};

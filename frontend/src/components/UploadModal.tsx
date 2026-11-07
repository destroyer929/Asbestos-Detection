"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Download,
  FolderOpen,
  Copy,
  Check,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { DrawingAnalysisResponse } from "@/types/drawing";
import { analyzeUploadedFile, getApiBaseUrl } from "@/lib/api";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (data: DrawingAnalysisResponse) => void;
}

// ─── Pipeline analysis stages ───────────────────────────────────────────────
const ANALYSIS_STAGES = [
  { id: "ingest",     minPct: 0,  maxPct: 15, label: "Ingesting blueprint file",       sublabel: "PDF / image router • multi-page detection" },
  { id: "preprocess", minPct: 15, maxPct: 35, label: "Adaptive preprocessing",         sublabel: "Sauvola binarization • line separation • deskew" },
  { id: "ocr",        minPct: 35, maxPct: 65, label: "Deep Learning OCR (CRAFT)",      sublabel: "Multi-scale text detection • bilingual recognition" },
  { id: "layout",     minPct: 65, maxPct: 80, label: "Layout & table analysis",        sublabel: "Finish Schedule detection • grid cell segmentation" },
  { id: "match",      minPct: 80, maxPct: 92, label: "4-Tier MLIT regulatory matching",sublabel: "Exact → rule → fuzzy → semantic MLIT verification" },
  { id: "finalize",   minPct: 92, maxPct: 100,label: "Finalizing safety report",      sublabel: "Hazard classification • review queue compilation" },
];

// ─── ProgressModal ───────────────────────────────────────────────────────────
const ProgressModal: React.FC<{
  filename: string;
  isComplete: boolean;
}> = ({ filename, isComplete }) => {
  const [percent, setPercent] = useState<number>(3);

  useEffect(() => {
    if (isComplete) {
      setPercent(100);
      return;
    }

    // Smooth, realistic progress timer
    const timer = setInterval(() => {
      setPercent((curr) => {
        if (curr >= 95) return curr;
        // Faster progression at start, steady through OCR, gentle deceleration near 95%
        const inc = curr < 20 ? 1.4 : curr < 50 ? 0.9 : curr < 75 ? 0.6 : 0.25;
        return Math.min(Math.round((curr + inc) * 10) / 10, 95);
      });
    }, 120);

    return () => clearInterval(timer);
  }, [isComplete]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-500/15 text-blue-400 flex-shrink-0">
            {isComplete ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
            )}
          </div>
          <div className="overflow-hidden">
            <h3 className="font-bold text-sm text-white">
              {isComplete ? "Analysis Complete!" : "Analysing Blueprint…"}
            </h3>
            <p className="text-[11px] text-slate-400 font-mono truncate">{filename}</p>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Overall Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-200">Overall Progress</span>
              <span className="font-mono font-bold text-blue-400">{Math.round(percent)}%</span>
            </div>
            <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
              <div
                className="h-full bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-400 rounded-full transition-all duration-150 ease-out shadow-sm shadow-blue-500/50"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>

          {/* Sequential Stages List */}
          <div className="space-y-2">
            {ANALYSIS_STAGES.map((stage) => {
              const isDone = isComplete || percent >= stage.maxPct;
              const isActive = !isComplete && percent >= stage.minPct && percent < stage.maxPct;
              const isPending = !isComplete && percent < stage.minPct;

              return (
                <div
                  key={stage.id}
                  className={`flex items-start gap-3 p-2.5 rounded-xl transition-all duration-200 ${
                    isActive
                      ? "bg-blue-950/60 border border-blue-500/50 shadow-md shadow-blue-900/20"
                      : isDone
                      ? "bg-emerald-950/25 border border-emerald-800/30 text-emerald-300"
                      : "border border-transparent opacity-35 text-slate-500"
                  }`}
                >
                  {/* Status Icon */}
                  <div className="flex-shrink-0 mt-0.5">
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : isActive ? (
                      <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-600" />
                    )}
                  </div>

                  {/* Stage Text & Details */}
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-xs font-semibold truncate ${
                        isDone
                          ? "text-emerald-300"
                          : isActive
                          ? "text-blue-200"
                          : "text-slate-500"
                      }`}
                    >
                      {stage.label}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                      {stage.sublabel}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-center text-[11px] text-slate-500 font-mono">
            Multi-page architectural blueprints are processed sheet-by-sheet · please wait
          </p>
        </div>
      </div>
    </div>
  );
};

// ─── Main UploadModal Component ──────────────────────────────────────────────
export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [genSuccessMessage, setGenSuccessMessage] = useState<string | null>(null);
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
    setIsUploading(true);
    setIsComplete(false);
    setErrorMessage(null);

    try {
      const result = await analyzeUploadedFile(selectedFile);
      setIsComplete(true);
      // Allow user to see 100% completion state briefly before transitioning
      setTimeout(() => {
        setIsUploading(false);
        setIsComplete(false);
        onUploadSuccess(result);
        onClose();
      }, 550);
    } catch (err: any) {
      setIsUploading(false);
      setIsComplete(false);
      setErrorMessage(err.message || "Failed to analyze document.");
    }
  };

  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(path);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  const handleGenerateNew = async () => {
    setIsGenerating(true);
    setErrorMessage(null);
    setGenSuccessMessage(null);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/samples/generate`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to generate blueprint");
      const data = await res.json();
      setGenSuccessMessage(`Created ${data.id}! Available for direct download below.`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to generate new sample.");
    } finally {
      setIsGenerating(false);
    }
  };

  // While uploading, show the dedicated ProgressModal overlay
  if (isUploading && selectedFile) {
    return (
      <ProgressModal
        filename={selectedFile.name}
        isComplete={isComplete}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">
                Upload & Analyse Architectural Blueprint
              </h3>
              <p className="text-xs text-slate-400">
                Vector CAD PDF, Scanned Blueprint, or DXF Drawing
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-40"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Upload Body */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
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
            className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-6 text-center cursor-pointer transition bg-slate-950/60 hover:bg-slate-950/90 group"
          >
            <Upload className="w-9 h-9 mx-auto mb-2 text-slate-500 group-hover:text-blue-400 transition" />
            <p className="text-sm font-semibold text-slate-200">
              Drag and drop blueprint here, or{" "}
              <span className="text-blue-400 underline">browse files</span>
            </p>
            <p className="text-xs text-slate-500 mt-1 font-mono">
              Supports: PDF (Scanned / Vector CAD), JPG, PNG, DXF
            </p>
          </div>

          {selectedFile && (
            <div className="p-3 bg-slate-950 rounded-xl border border-blue-500/50 flex items-center justify-between">
              <div className="flex items-center gap-2.5 overflow-hidden">
                <FileText className="w-5 h-5 text-blue-400 flex-shrink-0" />
                <div className="overflow-hidden">
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {selectedFile.name}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            </div>
          )}

          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {genSuccessMessage && (
            <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{genSuccessMessage}</span>
            </div>
          )}

          {/* Section: Download Ready-to-Test Samples */}
          <div className="bg-slate-950/90 rounded-xl p-3.5 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Download className="w-3.5 h-3.5 text-blue-400" />
                1-Click Download Sample Test Blueprints:
              </span>
              <button
                onClick={handleGenerateNew}
                disabled={isGenerating}
                className="text-[11px] font-semibold text-amber-300 hover:text-amber-200 flex items-center gap-1 bg-amber-500/10 hover:bg-amber-500/20 px-2 py-0.5 rounded border border-amber-500/30 transition disabled:opacity-40"
              >
                {isGenerating ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3 text-amber-400" />
                )}
                <span>Generate New</span>
              </button>
            </div>

            <p className="text-[11px] text-slate-400">
              Download any of these authentic Japanese blueprints to test the drag-and-drop uploader:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
              {[
                { file: "ALFRED-DWG-1982-004_scanned.pdf", color: "text-rose-400",   label: "DWG-1982-004.pdf" },
                { file: "ALFRED-DWG-1982-005_scanned.pdf", color: "text-amber-400",  label: "DWG-1982-005.pdf" },
                { file: "ALFRED-DWG-1982-004_scanned.jpg", color: "text-emerald-400",label: "DWG-1982-004.jpg" },
                { file: "ALFRED-DWG-1982-001_vector.pdf",  color: "text-blue-400",   label: "DWG-1982-001_vec.pdf" },
                { file: "ALFRED-DWG-1982-006_scanned.pdf", color: "text-purple-400", label: "DWG-1982-006_new.pdf" },
                { file: "ALFRED-DWG-1982-007_scanned.pdf", color: "text-cyan-400",   label: "DWG-1982-007_new.pdf" },
                { file: "ALFRED-DWG-1982-008_scanned.jpg", color: "text-pink-400",   label: "DWG-1982-008_new.jpg" },
              ].map(({ file, color, label }) => (
                <a
                  key={file}
                  href={`http://127.0.0.1:8000/api/v1/download/sample/${file}`}
                  download={file}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-200 hover:text-white transition group"
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <FileText className={`w-4 h-4 ${color} flex-shrink-0`} />
                    <span className="truncate text-[11px]">{label}</span>
                  </div>
                  <Download className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-400 flex-shrink-0" />
                </a>
              ))}
            </div>
          </div>

          {/* Section: Local File Location on Disk */}
          <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 text-[11px] space-y-1.5">
            <span className="text-slate-400 flex items-center gap-1.5 font-semibold">
              <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
              Direct Local Disk Locations on your PC:
            </span>
            {[
              "D:\\alfred\\data\\output\\pdf_test_suite",
              "D:\\alfred\\data\\output\\degraded",
            ].map((path) => (
              <div key={path} className="flex items-center justify-between bg-slate-900 p-2 rounded border border-slate-800 font-mono text-slate-300">
                <span className="truncate">{path}</span>
                <button
                  onClick={() => handleCopyPath(path)}
                  className="ml-2 text-slate-400 hover:text-white transition flex items-center gap-1"
                  title="Copy path"
                >
                  {copiedPath === path ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleAnalyze}
            disabled={!selectedFile || isUploading}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition shadow-md shadow-blue-600/30 disabled:opacity-40 disabled:pointer-events-none flex items-center gap-2"
          >
            <span>Diagnose Blueprint</span>
          </button>
        </div>
      </div>
    </div>
  );
};

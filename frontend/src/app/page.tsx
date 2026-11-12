"use client";

import React, { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { Navbar } from "@/components/Navbar";
import { KPIDashboard } from "@/components/KPIDashboard";
import { BlueprintCanvas } from "@/components/BlueprintCanvas";
import { InspectorPanel } from "@/components/InspectorPanel";
import { MaterialTable } from "@/components/MaterialTable";
import { FinishScheduleModal } from "@/components/FinishScheduleModal";
import { DatabaseModal } from "@/components/DatabaseModal";
import { ReviewHistoryModal } from "@/components/ReviewHistoryModal";
import { UploadModal } from "@/components/UploadModal";

import {
  DrawingAnalysisResponse,
  DiagnosisItem,
  BenchmarkSample,
  AsbestosStatus,
  HumanOverridePayload,
} from "@/types/drawing";
import {
  checkApiHealth,
  fetchBenchmarkSamples,
  analyzeBenchmarkSample,
  submitHumanOverride,
  fetchDrawingPage,
  fetchDrawingHistory,
} from "@/lib/api";
import {
  Loader2,
  AlertCircle,
  X,
  Upload,
  FileUp,
  Sparkles,
  Database,
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  Building2,
  FileText,
} from "lucide-react";

export default function HomePage() {
  // Backend status & samples
  const [health, setHealth] = useState<{
    status: string;
    gpu_available: boolean;
    database_entries: number;
  } | null>(null);
  const [samples, setSamples] = useState<BenchmarkSample[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("");
  const [databaseCount, setDatabaseCount] = useState<number>(0);

  // Analysis result
  const [analysis, setAnalysis] = useState<DrawingAnalysisResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DiagnosisItem | null>(null);
  const [activeFilter, setActiveFilter] = useState<AsbestosStatus | "ALL">("ALL");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isPageLoading, setIsPageLoading] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isScheduleOpen, setIsScheduleOpen] = useState<boolean>(false);
  const [isDatabaseOpen, setIsDatabaseOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);

  // Refresh database history count
  const refreshHistoryCount = useCallback(async () => {
    try {
      const historyItems = await fetchDrawingHistory();
      setDatabaseCount(historyItems.length);
    } catch {
      // ignore
    }
  }, []);

  // Load a sample blueprint
  const loadSample = useCallback(async (sampleId: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await analyzeBenchmarkSample(sampleId);
      setAnalysis(data);
      setSelectedSampleId(sampleId);
      setCurrentPage(data.current_page || 1);
      setErrorMessage(null);

      // Select first positive or uncertain item by default, or first item
      if (data.diagnoses && data.diagnoses.length > 0) {
        const priorityItem =
          data.diagnoses.find((d) => d.status === "POSITIVE") ||
          data.diagnoses.find((d) => d.status === "UNCERTAIN") ||
          data.diagnoses[0];
        setSelectedItem(priorityItem);
      } else {
        setSelectedItem(null);
      }
      refreshHistoryCount();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load sample blueprint.");
    } finally {
      setIsLoading(false);
    }
  }, [refreshHistoryCount]);

  // Clear active analysis and return to upload prompt
  const handleClearAnalysis = () => {
    setAnalysis(null);
    setSelectedItem(null);
    setSelectedSampleId("");
    setErrorMessage(null);
  };

  // Initial load - fetch system health and preset catalog without auto-analyzing any file
  useEffect(() => {
    let mounted = true;
    async function init() {
      try {
        const [h, sList] = await Promise.all([
          checkApiHealth(),
          fetchBenchmarkSamples(),
        ]);
        if (!mounted) return;
        setHealth(h);
        setSamples(sList);
        refreshHistoryCount();
      } catch (err: any) {
        if (mounted) {
          setErrorMessage(err.message || "Failed to initialize blueprint analysis.");
        }
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, [refreshHistoryCount]);

  // Handle uploaded drawing
  const handleUploadSuccess = (data: DrawingAnalysisResponse) => {
    setAnalysis(data);
    setSelectedSampleId(data.drawing_id);
    setCurrentPage(data.current_page || 1);
    if (data.diagnoses && data.diagnoses.length > 0) {
      const priorityItem =
        data.diagnoses.find((d) => d.status === "POSITIVE") ||
        data.diagnoses.find((d) => d.status === "UNCERTAIN") ||
        data.diagnoses[0];
      setSelectedItem(priorityItem);
    } else {
      setSelectedItem(null);
    }
    refreshHistoryCount();
  };

  // Handle loading drawing from historical database
  const handleLoadFromHistory = (drawingData: DrawingAnalysisResponse) => {
    setAnalysis(drawingData);
    setSelectedSampleId(drawingData.drawing_id);
    setCurrentPage(drawingData.current_page || 1);
    if (drawingData.diagnoses && drawingData.diagnoses.length > 0) {
      const priorityItem =
        drawingData.diagnoses.find((d) => d.status === "POSITIVE") ||
        drawingData.diagnoses.find((d) => d.status === "UNCERTAIN") ||
        drawingData.diagnoses[0];
      setSelectedItem(priorityItem);
    } else {
      setSelectedItem(null);
    }
    setIsDatabaseOpen(false);
  };

  // Change active page in multi-page document
  const handlePageChange = async (newPage: number) => {
    if (!analysis || newPage === currentPage) return;
    setIsPageLoading(true);
    try {
      const pageData = await fetchDrawingPage(analysis.drawing_id, newPage);
      setCurrentPage(newPage);
      setAnalysis({
        ...analysis,
        current_page: newPage,
        image_base64: pageData.image_base64,
        image_width: pageData.image_width,
        image_height: pageData.image_height,
        table_bbox: pageData.table_bbox,
      });

      // Select first item on the newly viewed page if available
      const pageItems = analysis.diagnoses.filter((d) => (d.page_number || 1) === newPage);
      if (pageItems.length > 0) {
        setSelectedItem(pageItems[0]);
      }
    } catch (err: any) {
      console.error("Failed to load page:", err);
    } finally {
      setIsPageLoading(false);
    }
  };

  // Human active learning override handler
  const handleOverrideSuccess = (updatedItem: DiagnosisItem) => {
    if (!analysis) return;
    const updatedDiagnoses = analysis.diagnoses.map((d) =>
      d.item_id === updatedItem.item_id ? updatedItem : d
    );

    // Recalculate summary metrics
    const pos = updatedDiagnoses.filter((d) => d.status === "POSITIVE").length;
    const neg = updatedDiagnoses.filter((d) => d.status === "NEGATIVE").length;
    const unc = updatedDiagnoses.filter((d) => d.status === "UNCERTAIN").length;
    const rev = updatedDiagnoses.filter((d) => d.requires_human_review).length;

    const l1 = updatedDiagnoses.filter((d) => d.hazard_level === "LEVEL_1").length;
    const l2 = updatedDiagnoses.filter((d) => d.hazard_level === "LEVEL_2").length;
    const l3 = updatedDiagnoses.filter((d) => d.hazard_level === "LEVEL_3").length;

    setAnalysis({
      ...analysis,
      diagnoses: updatedDiagnoses,
      summary: {
        asbestos_positive: pos,
        non_asbestos: neg,
        uncertain: unc,
        review_required: rev,
        hazard_levels: {
          level_1_sprays: l1,
          level_2_insulation: l2,
          level_3_molded: l3,
        },
      },
    });

    setSelectedItem(updatedItem);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f7fbf6] text-slate-800">
      {/* Navigation */}
      <Navbar
        health={health}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenSchedule={() => setIsScheduleOpen(true)}
        onOpenDatabase={() => {
          refreshHistoryCount();
          setIsDatabaseOpen(true);
        }}
        onOpenHistory={() => setIsHistoryOpen(true)}
        isLoading={isLoading}
        databaseCount={databaseCount}
      />

      {/* Main Workspace Content */}
      <main className="flex-1 max-w-[1920px] w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-4 p-4 rounded-2xl bg-rose-50 border border-rose-300 text-rose-800 text-sm flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
              <span className="font-medium">{errorMessage}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => loadSample(selectedSampleId)}
                className="px-3.5 py-1.5 rounded-full bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition shadow-xs"
              >
                Retry
              </button>
              <button
                onClick={() => setErrorMessage(null)}
                className="p-1 rounded-full hover:bg-rose-100 text-rose-600 hover:text-rose-800 transition"
                title="Dismiss alert"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && !analysis && (
          <div className="h-[65vh] flex flex-col items-center justify-center text-slate-600">
            <div className="relative mb-6">
              <div className="w-20 h-20 rounded-3xl bg-white border border-emerald-200 flex items-center justify-center shadow-lg shadow-emerald-500/10">
                <Image
                  src="/brand/bird.png"
                  alt="Alfred Logo"
                  width={48}
                  height={48}
                  className="object-contain"
                />
              </div>
              <Loader2 className="w-8 h-8 animate-spin text-emerald-600 absolute -bottom-2 -right-2 bg-white rounded-full p-1 border border-emerald-300 shadow-sm" />
            </div>
            <p className="font-extrabold text-base text-slate-900 tracking-wide">
              Analyzing Architectural Blueprint & Material Schedules...
            </p>
            <p className="text-xs text-emerald-700 mt-1.5 font-lab-mono font-medium">
              PaddleOCR CJK • Deskew Normalization • 4-Tier MLIT Matching • Tier-5 LLM Arbitration
            </p>
          </div>
        )}

        {/* Upload Sample to Diagnosis Landing State (Green + White Clean Theme) */}
        {!analysis && !isLoading && (
          <div className="max-w-4xl mx-auto my-6 sm:my-10 px-4">
            <div className="bg-white rounded-3xl p-8 sm:p-12 text-center relative overflow-hidden border border-emerald-200/90 shadow-xl shadow-emerald-900/5">
              {/* Soft decorative background tint */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[550px] h-48 bg-emerald-100/40 rounded-full blur-3xl pointer-events-none" />

              {/* Alfred Brand Logo Emblem */}
              <div className="relative w-24 h-24 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-emerald-50 via-white to-emerald-50/50 flex items-center justify-center shadow-md shadow-emerald-900/10 ring-8 ring-emerald-500/10 border border-emerald-300">
                <Image
                  src="/brand/bird.png"
                  alt="Alfred Logo"
                  width={56}
                  height={56}
                  className="object-contain filter drop-shadow-sm"
                  priority
                />
              </div>

              {/* Japanese Precision Tagline */}
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-[11px] font-bold text-emerald-800 mb-3 font-lab-mono shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>BUILT ON JAPANESE PRECISION • REIMAGINED FOR INDIA</span>
              </div>

              {/* Headline */}
              <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                Upload sample to diagnosis
              </h1>
              <p className="text-sm font-bold text-[#28a745] mt-2 font-sans">
                図面・サンプルをアップロードして石綿診断を開始
              </p>

              <p className="max-w-2xl mx-auto text-sm text-slate-600 mt-3.5 leading-relaxed font-sans">
                2 Countries. 3+ Labs. 1 leading Asbestos Analysis platform. Upload architectural blueprints (PDF, High-Res Scanned JPG/PNG, CAD DXF) to run automated MLIT-compliant detection, PaddleOCR text extraction, and regulatory arbitration.
              </p>

              {/* Primary Action Buttons (Green + White) */}
              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3.5">
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="btn-hover-shine w-full sm:w-auto px-7 py-3.5 rounded-full bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white font-bold text-sm flex items-center justify-center gap-2.5 shadow-lg shadow-emerald-600/25 transition active:scale-95"
                >
                  <Upload className="w-4 h-4" />
                  <span>Upload Blueprint / 図面アップロード</span>
                </button>

                <button
                  onClick={() => {
                    refreshHistoryCount();
                    setIsDatabaseOpen(true);
                  }}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-full bg-white hover:bg-emerald-50/70 text-emerald-800 font-bold text-sm border border-emerald-300 hover:border-emerald-500 flex items-center justify-center gap-2.5 transition shadow-sm"
                >
                  <Database className="w-4 h-4 text-emerald-600" />
                  <span>Open Database ({databaseCount} saved)</span>
                </button>
              </div>


            </div>
          </div>
        )}

        {analysis && (
          <>
            {/* Active Drawing Top Bar & Reset/Upload CTA */}
            <div className="mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-white border-2 border-emerald-300 shadow-sm backdrop-blur-md">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleClearAnalysis}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-bold border border-emerald-200 transition"
                  title="Return to upload screen"
                >
                  <ArrowLeft className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Upload Another Drawing</span>
                </button>
                <div className="h-4 w-[1px] bg-emerald-200 hidden sm:block" />
                <div>
                  <span className="text-xs text-slate-500 font-lab-mono">Active File: </span>
                  <span className="text-xs font-bold text-slate-900 font-lab-mono">{analysis.filename}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="btn-hover-shine flex items-center gap-1.5 px-4 py-2 rounded-full bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white text-xs font-bold transition shadow-sm shadow-emerald-500/20"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>New Upload</span>
                </button>
              </div>
            </div>

            {/* KPI Dashboard */}
            <KPIDashboard
              summary={analysis.summary}
              totalAnnotations={analysis.total_material_annotations}
              activeFilter={activeFilter}
              onFilterChange={(f) => setActiveFilter(f)}
              documentType={analysis.document_type}
              isVector={analysis.is_vector_pdf}
              qualityAssessment={analysis.quality_assessment}
            />

            {/* Split Grid: Canvas (Left) + Inspector (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
              {/* Interactive Canvas: 8 cols on large screens */}
              <div className="lg:col-span-8">
                <BlueprintCanvas
                  imageBase64={analysis.image_base64}
                  imageWidth={analysis.image_width}
                  imageHeight={analysis.image_height}
                  diagnoses={analysis.diagnoses}
                  selectedItem={selectedItem}
                  onSelectItem={(item) => setSelectedItem(item)}
                  tableBbox={analysis.table_bbox}
                  activeFilter={activeFilter}
                  currentPage={currentPage}
                  pageCount={analysis.page_count || 1}
                  onPageChange={handlePageChange}
                  isPageLoading={isPageLoading}
                  roomAssessments={analysis.room_assessments}
                />
              </div>

              {/* Inspector & Override Panel: 4 cols on large screens */}
              <div className="lg:col-span-4 h-[540px] lg:h-[620px] xl:h-[680px]">
                <InspectorPanel
                  drawingId={analysis.drawing_id}
                  diagnoses={analysis.diagnoses}
                  selectedItem={selectedItem}
                  onSelectItem={(item) => setSelectedItem(item)}
                  onOverrideSuccess={handleOverrideSuccess}
                  onSubmitOverride={submitHumanOverride}
                  qualityAssessment={analysis.quality_assessment}
                />
              </div>
            </div>

            {/* Bottom Full Annotation & Material Inspection Table */}
            <MaterialTable
              diagnoses={analysis.diagnoses}
              selectedItem={selectedItem}
              onSelectItem={(item) => {
                setSelectedItem(item);
                if (item.page_number && item.page_number !== currentPage) {
                  handlePageChange(item.page_number);
                }
              }}
              activeFilter={activeFilter}
              filename={analysis.filename}
            />
          </>
        )}
      </main>

      {/* Modals */}
      <FinishScheduleModal
        isOpen={isScheduleOpen}
        onClose={() => setIsScheduleOpen(false)}
        schedule={analysis?.finish_schedule || []}
        filename={analysis?.filename || ""}
      />

      <DatabaseModal
        isOpen={isDatabaseOpen}
        onClose={() => setIsDatabaseOpen(false)}
        onLoadDrawing={handleLoadFromHistory}
      />

      <ReviewHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
      />

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}

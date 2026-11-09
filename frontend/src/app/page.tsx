"use client";

import React, { useState, useEffect, useCallback } from "react";
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
import { Loader2, AlertCircle, X, Upload, FileUp, Sparkles, Database, ArrowLeft, RefreshCw } from "lucide-react";

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
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
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
          <div className="mb-4 p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-sm flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => loadSample(selectedSampleId)}
                className="px-3 py-1 rounded-lg bg-rose-900 hover:bg-rose-800 text-xs font-semibold transition"
              >
                Retry
              </button>
              <button
                onClick={() => setErrorMessage(null)}
                className="p-1 rounded-lg hover:bg-rose-900/60 text-rose-400 hover:text-rose-200 transition"
                title="Dismiss alert"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && !analysis && (
          <div className="h-[60vh] flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-3" />
            <p className="font-semibold text-sm">
              Loading Architectural Blueprint & Deep Learning OCR Diagnostics...
            </p>
            <p className="text-xs text-slate-500 mt-1 font-mono">
              Running Ingestion Router • Deskew Normalization • 4-Tier MLIT Matcher
            </p>
          </div>
        )}

        {/* Upload Sample to Diagnosis Landing State (Initial empty screen) */}
        {!analysis && !isLoading && (
          <div className="max-w-4xl mx-auto my-8 sm:my-12 px-4">
            <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-8 sm:p-12 shadow-2xl backdrop-blur-sm text-center relative overflow-hidden">
              {/* Decorative background glow */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-36 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

              {/* Main Icon */}
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-xl shadow-blue-500/25 ring-8 ring-blue-500/10">
                <FileUp className="w-10 h-10 text-white" />
              </div>

              {/* Headline */}
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Upload sample to diagnosis
              </h1>
              <p className="text-sm font-semibold text-blue-400 mt-1.5">
                図面・サンプルをアップロードして石綿診断を開始
              </p>

              <p className="max-w-xl mx-auto text-sm text-slate-400 mt-3 leading-relaxed">
                Upload an architectural blueprint (PDF, Scanned JPG/PNG, CAD DXF) to run automated MLIT-compliant asbestos detection, OCR text extraction, 4-Tier matching, and Tier-5 LLM arbitration.
              </p>

              {/* Primary Action Buttons */}
              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition transform hover:-translate-y-0.5 active:translate-y-0"
                >
                  <Upload className="w-4 h-4" />
                  <span>Upload Blueprint / 図面アップロード</span>
                </button>

                <button
                  onClick={() => {
                    refreshHistoryCount();
                    setIsDatabaseOpen(true);
                  }}
                  className="w-full sm:w-auto px-5 py-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-sm border border-slate-700 flex items-center justify-center gap-2 transition"
                >
                  <Database className="w-4 h-4 text-cyan-400" />
                  <span>Open Database ({databaseCount} saved)</span>
                </button>
              </div>

              {/* Preset benchmark samples section */}
              {samples.length > 0 && (
                <div className="mt-12 pt-8 border-t border-slate-800/80 text-left">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                      Or choose a preset benchmark sample:
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {samples.length} presets available
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                    {samples.slice(0, 6).map((sample) => (
                      <button
                        key={sample.id}
                        onClick={() => loadSample(sample.id)}
                        className="p-3.5 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800 hover:border-blue-500/50 text-left transition group"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[11px] font-mono font-bold text-blue-400 group-hover:text-blue-300 truncate mr-2">
                            {sample.id}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono flex-shrink-0">
                            {sample.doc_type}
                          </span>
                        </div>
                        <p className="text-xs font-semibold text-slate-200 group-hover:text-white line-clamp-1">
                          {sample.title}
                        </p>
                        <p className="text-[11px] text-slate-500 line-clamp-2 mt-1">
                          {sample.description}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {analysis && (
          <>
            {/* Active Drawing Top Bar & Reset/Upload CTA */}
            <div className="mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleClearAnalysis}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 transition"
                  title="Return to upload screen"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Upload Another Drawing</span>
                </button>
                <div className="h-4 w-[1px] bg-slate-800 hidden sm:block" />
                <div>
                  <span className="text-xs text-slate-400 font-mono">Current File: </span>
                  <span className="text-xs font-bold text-white font-mono">{analysis.filename}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition shadow shadow-blue-600/30"
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
              <div className="lg:col-span-4 h-[640px] lg:h-[720px]">
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

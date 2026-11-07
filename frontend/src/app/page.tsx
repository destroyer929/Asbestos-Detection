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
import { Loader2, AlertCircle, X } from "lucide-react";

export default function HomePage() {
  // Backend status & samples
  const [health, setHealth] = useState<{
    status: string;
    gpu_available: boolean;
    database_entries: number;
  } | null>(null);
  const [samples, setSamples] = useState<BenchmarkSample[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("ALFRED-DWG-1982-001");
  const [databaseCount, setDatabaseCount] = useState<number>(0);

  // Analysis result
  const [analysis, setAnalysis] = useState<DrawingAnalysisResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DiagnosisItem | null>(null);
  const [activeFilter, setActiveFilter] = useState<AsbestosStatus | "ALL">("ALL");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isPageLoading, setIsPageLoading] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
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

  // Initial load
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

        const defaultId = sList.find(s => s.id === "ALFRED-DWG-1982-001")?.id || (sList.length > 0 ? sList[0].id : "ALFRED-DWG-1982-001");
        setSelectedSampleId(defaultId);
        await loadSample(defaultId);
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
  }, [loadSample, refreshHistoryCount]);

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
        onOpenDatabase={() => setIsDatabaseOpen(true)}
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

        {analysis && (
          <>
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

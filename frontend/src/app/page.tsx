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
  fetchJobStatus,
} from "@/lib/api";
import { Loader2, AlertCircle, Layers } from "lucide-react";

export default function HomePage() {
  // Backend status & samples
  const [health, setHealth] = useState<{
    status: string;
    gpu_available: boolean;
    database_entries: number;
  } | null>(null);
  const [samples, setSamples] = useState<BenchmarkSample[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("ALFRED-DWG-1982-001");

  // Analysis result
  const [analysis, setAnalysis] = useState<DrawingAnalysisResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DiagnosisItem | null>(null);
  const [activeFilter, setActiveFilter] = useState<AsbestosStatus | "ALL">("ALL");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isPageLoading, setIsPageLoading] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<{
    status: string;
    completed_count: number;
    total_pages: number;
    progress_percent: number;
    current_status: string;
  } | null>(null);

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isScheduleOpen, setIsScheduleOpen] = useState<boolean>(false);
  const [isDatabaseOpen, setIsDatabaseOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);

  // Load a sample blueprint
  const loadSample = useCallback(async (sampleId: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await analyzeBenchmarkSample(sampleId);
      setAnalysis(data);
      setSelectedSampleId(sampleId);
      setCurrentPage(data.current_page || 1);

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
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load sample blueprint.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    async function init() {
      const [h, sList] = await Promise.all([
        checkApiHealth(),
        fetchBenchmarkSamples(),
      ]);
      setHealth(h);
      setSamples(sList);

      const defaultId = sList.length > 0 ? sList[0].id : "ALFRED-DWG-1982-001";
      setSelectedSampleId(defaultId);
      loadSample(defaultId);
    }

    init();
  }, [loadSample]);

  // Handle uploaded drawing
  const handleUploadSuccess = (data: DrawingAnalysisResponse) => {
    setAnalysis(data);
    setSelectedSampleId(data.drawing_id);
    setCurrentPage(data.current_page || 1);
    if (data.status === "processing" && (data.page_count || 1) > 1) {
      setJobStatus({
        status: "processing",
        completed_count: 1,
        total_pages: data.page_count || 1,
        progress_percent: Math.round((1 / (data.page_count || 1)) * 100),
        current_status: `Page 1 ready. Analyzing remaining ${(data.page_count || 1) - 1} pages in background...`,
      });
    } else {
      setJobStatus(null);
    }
    if (data.diagnoses && data.diagnoses.length > 0) {
      const priorityItem =
        data.diagnoses.find((d) => d.status === "POSITIVE") ||
        data.diagnoses.find((d) => d.status === "UNCERTAIN") ||
        data.diagnoses[0];
      setSelectedItem(priorityItem);
    } else {
      setSelectedItem(null);
    }
  };

  // Poll background job status for multi-page blueprints
  useEffect(() => {
    if (!analysis || analysis.status !== "processing" || (analysis.page_count || 1) <= 1) {
      return;
    }
    const interval = setInterval(async () => {
      const status = await fetchJobStatus(analysis.drawing_id);
      if (status) {
        setJobStatus(status);
        if (status.status === "completed") {
          setAnalysis((prev) => (prev ? { ...prev, status: "completed" } : prev));
          clearInterval(interval);
        }
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [analysis?.drawing_id, analysis?.status, analysis?.page_count]);

  // Change active page in multi-page document
  const handlePageChange = async (newPage: number) => {
    if (!analysis || newPage === currentPage) return;
    setIsPageLoading(true);
    try {
      const pageData = await fetchDrawingPage(analysis.drawing_id, newPage);
      setCurrentPage(newPage);

      // Merge new page diagnoses into all diagnoses
      let updatedDiagnoses = analysis.diagnoses;
      if (pageData.diagnoses && pageData.diagnoses.length > 0) {
        const otherPages = analysis.diagnoses.filter((d) => (d.page_number || 1) !== newPage);
        updatedDiagnoses = [...otherPages, ...pageData.diagnoses];
      }

      setAnalysis({
        ...analysis,
        current_page: newPage,
        image_base64: pageData.image_base64 || analysis.image_base64,
        image_width: pageData.image_width || analysis.image_width,
        image_height: pageData.image_height || analysis.image_height,
        table_bbox: pageData.table_bbox !== undefined ? pageData.table_bbox : analysis.table_bbox,
        finish_schedule: (pageData.finish_schedule && pageData.finish_schedule.length > 0)
          ? pageData.finish_schedule
          : analysis.finish_schedule,
        room_assessments: pageData.room_assessments || analysis.room_assessments,
        diagnoses: updatedDiagnoses,
      });

      // Select first item on the newly viewed page
      const pageItems = updatedDiagnoses.filter((d) => (d.page_number || 1) === newPage);
      if (pageItems.length > 0) {
        const priorityItem =
          pageItems.find((d) => d.status === "POSITIVE") ||
          pageItems.find((d) => d.status === "UNCERTAIN") ||
          pageItems[0];
        setSelectedItem(priorityItem);
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
      />

      {/* Main Workspace Content */}
      <main className="flex-1 max-w-[1920px] w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-4 p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => loadSample(selectedSampleId)}
              className="px-3 py-1 rounded-lg bg-rose-900 hover:bg-rose-800 text-xs font-semibold"
            >
              Retry
            </button>
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
            {/* Background Multi-Page Processing Banner */}
            {jobStatus && jobStatus.status === "processing" && (
              <div className="mb-4 p-3.5 rounded-xl bg-blue-950/70 border border-blue-800 text-blue-200 text-xs flex items-center justify-between shadow-lg animate-fadeIn">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400 flex-shrink-0" />
                  <div>
                    <span className="font-semibold text-white">Hierarchical Pipeline Active:</span>{" "}
                    <span>Page 1 is ready for inspection. Analyzing remaining pages in the background...</span>
                    <span className="ml-2 font-mono text-blue-300 font-bold">
                      [{jobStatus.completed_count}/{jobStatus.total_pages} pages • {jobStatus.progress_percent}%]
                    </span>
                  </div>
                </div>
                <div className="w-32 bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700 hidden sm:block">
                  <div
                    className="bg-blue-500 h-full transition-all duration-300 rounded-full"
                    style={{ width: `${jobStatus.progress_percent}%` }}
                  />
                </div>
              </div>
            )}

            {/* KPI Dashboard */}
            <KPIDashboard
              summary={analysis.summary}
              totalAnnotations={analysis.total_material_annotations}
              activeFilter={activeFilter}
              onFilterChange={(f) => setActiveFilter(f)}
              documentType={analysis.document_type}
              isVector={analysis.is_vector_pdf}
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

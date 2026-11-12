"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  X,
  Database,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Flame,
  Layers,
  Box,
  Search,
  FileText,
  ArrowUpRight,
  Trash2,
  Download,
  Calendar,
  ChevronLeft,
  CheckCircle2,
  Clock,
  Sparkles,
  FileSpreadsheet,
  Building2,
  RefreshCw,
} from "lucide-react";
import {
  DatabaseSummary,
  DrawingHistorySummary,
  DrawingHistoryDetail,
  DrawingAnalysisResponse,
  DiagnosisItem,
} from "@/types/drawing";
import {
  fetchDatabaseSummary,
  fetchDrawingHistory,
  fetchDrawingHistoryDetail,
  deleteDrawingHistory,
} from "@/lib/api";

interface DatabaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadDrawing?: (drawing: DrawingAnalysisResponse) => void;
}

export const DatabaseModal: React.FC<DatabaseModalProps> = ({
  isOpen,
  onClose,
  onLoadDrawing,
}) => {
  const [activeTab, setActiveTab] = useState<"history" | "mlit_db">("history");
  const [historyList, setHistoryList] = useState<DrawingHistorySummary[]>([]);
  const [mlitSummary, setMlitSummary] = useState<DatabaseSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "HAZARDOUS" | "SAFE" | "REVIEW">("ALL");

  // Detailed Report View state for a specific file
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<DrawingHistoryDetail | null>(null);
  const [isReportLoading, setIsReportLoading] = useState<boolean>(false);
  const [reportSearchQuery, setReportSearchQuery] = useState<string>("");
  const [reportFilter, setReportFilter] = useState<"ALL" | "POSITIVE" | "NEGATIVE" | "UNCERTAIN">("ALL");

  // Load history list & MLIT summary when modal opens
  const refreshHistory = async () => {
    setIsLoading(true);
    try {
      const [historyData, mlitData] = await Promise.all([
        fetchDrawingHistory(),
        fetchDatabaseSummary(),
      ]);
      console.log("Database modal loaded history records:", historyData);
      setHistoryList(Array.isArray(historyData) ? historyData : []);
      setMlitSummary(mlitData);
    } catch (err) {
      console.error("Failed to load history database:", err);
      setHistoryList([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      refreshHistory();
      setSelectedReportId(null);
      setReportDetail(null);
    }
  }, [isOpen]);

  // Load detailed diagnosis report when a file is selected
  const handleOpenReport = async (drawingId: string) => {
    setSelectedReportId(drawingId);
    setIsReportLoading(true);
    try {
      const detail = await fetchDrawingHistoryDetail(drawingId);
      setReportDetail(detail);
    } catch (err) {
      console.error(`Failed to load detail for drawing ${drawingId}:`, err);
    } finally {
      setIsReportLoading(false);
    }
  };

  // Delete a record from history
  const handleDeleteRecord = async (drawingId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete "${drawingId}" from the analysis database?`)) {
      try {
        await deleteDrawingHistory(drawingId);
        setHistoryList((prev) => prev.filter((item) => item.drawing_id !== drawingId));
        if (selectedReportId === drawingId) {
          setSelectedReportId(null);
          setReportDetail(null);
        }
      } catch (err) {
        alert("Failed to delete record: " + err);
      }
    }
  };

  // Load file into active workspace
  const handleLoadIntoWorkspace = async (drawingId: string) => {
    try {
      let dataToLoad: DrawingAnalysisResponse;
      if (reportDetail && reportDetail.drawing_id === drawingId) {
        dataToLoad = reportDetail;
      } else {
        dataToLoad = await fetchDrawingHistoryDetail(drawingId);
      }
      if (onLoadDrawing) {
        onLoadDrawing(dataToLoad);
        onClose();
      }
    } catch (err) {
      alert("Failed to load blueprint into workspace: " + err);
    }
  };

  // Filter history records safely
  const filteredHistory = useMemo(() => {
    if (!Array.isArray(historyList)) return [];
    return historyList.filter((item) => {
      const filename = (item?.filename || "").toLowerCase();
      const drawingId = (item?.drawing_id || "").toLowerCase();
      const posMaterials = Array.isArray(item?.positive_materials) ? item.positive_materials : [];
      const query = (searchQuery || "").toLowerCase().trim();

      const matchesSearch =
        !query ||
        filename.includes(query) ||
        drawingId.includes(query) ||
        posMaterials.some((m) => (m || "").toLowerCase().includes(query));

      if (!matchesSearch) return false;

      const pos = item?.summary?.asbestos_positive || 0;
      const unc = item?.summary?.uncertain || 0;
      const rev = item?.summary?.review_required || 0;

      if (statusFilter === "HAZARDOUS") {
        return pos > 0;
      }
      if (statusFilter === "SAFE") {
        return pos === 0 && unc === 0 && rev === 0;
      }
      if (statusFilter === "REVIEW") {
        return unc > 0 || rev > 0;
      }
      return true;
    });
  }, [historyList, searchQuery, statusFilter]);

  // Filter diagnoses in the detailed report view
  const filteredReportDiagnoses = useMemo(() => {
    if (!reportDetail?.diagnoses || !Array.isArray(reportDetail.diagnoses)) return [];
    return reportDetail.diagnoses.filter((diag) => {
      const query = (reportSearchQuery || "").toLowerCase().trim();
      const raw = (diag?.raw_text || "").toLowerCase();
      const ja = (diag?.matched_material_ja || "").toLowerCase();
      const en = (diag?.matched_material_en || "").toLowerCase();
      const cite = (diag?.regulatory_citation || "").toLowerCase();

      const matchesSearch =
        !query ||
        raw.includes(query) ||
        ja.includes(query) ||
        en.includes(query) ||
        cite.includes(query);

      if (!matchesSearch) return false;

      if (reportFilter !== "ALL" && diag?.status !== reportFilter) {
        return false;
      }
      return true;
    });
  }, [reportDetail, reportSearchQuery, reportFilter]);

  // Export functions
  const handleExportJSON = () => {
    if (!reportDetail) return;
    const blob = new Blob([JSON.stringify(reportDetail, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `DIAGNOSIS-REPORT-${reportDetail.drawing_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!reportDetail?.diagnoses) return;
    const headers = [
      "Item ID",
      "Status",
      "Hazard Level",
      "Raw Text",
      "Matched Material (JA)",
      "Matched Material (EN)",
      "Confidence (%)",
      "Match Tier",
      "Regulatory Citation",
    ];
    const rows = reportDetail.diagnoses.map((d) => [
      d.item_id || "",
      d.status || "",
      d.hazard_level || "",
      `"${(d.raw_text || "").replace(/"/g, '""')}"`,
      `"${(d.matched_material_ja || "").replace(/"/g, '""')}"`,
      `"${(d.matched_material_en || "").replace(/"/g, '""')}"`,
      ((d.confidence || 0) * 100).toFixed(1),
      d.match_tier || "",
      `"${(d.regulatory_citation || "").replace(/"/g, '""')}"`,
    ]);

    const csvContent = "\uFEFF" + [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `DIAGNOSIS-ITEMS-${reportDetail.drawing_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/40 backdrop-blur-md animate-fadeIn">
      <div className="bg-white border-2 border-emerald-300 rounded-3xl w-full max-w-6xl h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header Bar */}
        <div className="p-4 bg-emerald-50/80 border-b-2 border-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-white text-emerald-600 border-2 border-emerald-200 shadow-2xs">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-base text-slate-900 tracking-wide">
                  Alfred Database (図面データベース & 診断履歴)
                </h3>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 font-lab-mono">
                  {historyList.length} Checked Files
                </span>
              </div>
              <p className="text-xs text-slate-600 font-sans mt-0.5">
                Persistent repository of previously analyzed blueprints, historical records, and MLIT / JIS A 1481 diagnosis reports
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={refreshHistory}
              title="Refresh records"
              className="p-2 rounded-full text-slate-500 hover:text-emerald-800 hover:bg-emerald-50 transition"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-emerald-600" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-full text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center justify-between px-6 pt-3 bg-white border-b-2 border-emerald-100 font-lab-mono">
          <div className="flex gap-2">
            <button
              onClick={() => {
                setActiveTab("history");
                setSelectedReportId(null);
                setReportDetail(null);
              }}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-t-xl transition border-b-2 ${
                activeTab === "history"
                  ? "text-emerald-800 border-emerald-600 bg-emerald-50/80"
                  : "text-slate-500 border-transparent hover:text-slate-800"
              }`}
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <span>Checked Files & Reports ({historyList.length})</span>
            </button>
            <button
              onClick={() => {
                setActiveTab("mlit_db");
                setSelectedReportId(null);
              }}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-t-xl transition border-b-2 ${
                activeTab === "mlit_db"
                  ? "text-emerald-800 border-emerald-600 bg-emerald-50/80"
                  : "text-slate-500 border-transparent hover:text-slate-800"
              }`}
            >
              <Layers className="w-4 h-4 text-emerald-600" />
              <span>MLIT Reference Specifications (国土交通省基準)</span>
            </button>
          </div>

          {selectedReportId && activeTab === "history" && (
            <button
              onClick={() => {
                setSelectedReportId(null);
                setReportDetail(null);
              }}
              className="flex items-center gap-1.5 text-xs font-bold text-emerald-800 hover:text-emerald-950 px-3.5 py-1.5 rounded-full bg-white hover:bg-emerald-50 border-2 border-emerald-300 transition mb-2 shadow-2xs"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Back to Files List</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#f7fbf6]">
          {activeTab === "history" ? (
            selectedReportId && reportDetail ? (
              /* DETAILED REPORT VIEW FOR A SINGLE FILE (Green + White Clean Theme) */
              <div className="space-y-5">
                {/* Report Header Card */}
                <div className="bg-white border-2 border-emerald-300 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className="font-lab-mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                        {reportDetail.drawing_id}
                      </span>
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-emerald-600" />
                        Analyzed: {reportDetail.timestamp || "Archived"}
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-lab-mono font-medium">
                        {reportDetail.document_type || "DRAWING"}
                      </span>
                    </div>
                    <h2 className="text-xl font-extrabold text-slate-900 mt-2 flex items-center gap-2">
                      {reportDetail.filename}
                    </h2>
                    <p className="text-xs text-slate-600 mt-1 font-sans">
                      {reportDetail.total_material_annotations || 0} total material annotations identified across {reportDetail.page_count || 1} sheet(s)
                    </p>
                  </div>

                  {/* Actions & Verdict */}
                  <div className="flex flex-wrap items-center gap-2.5">
                    <button
                      onClick={() => handleLoadIntoWorkspace(reportDetail.drawing_id)}
                      className="btn-hover-shine flex items-center gap-1.5 bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white text-xs font-bold px-4 py-2.5 rounded-full transition shadow-md shadow-emerald-600/20 active:scale-95"
                    >
                      <ArrowUpRight className="w-4 h-4" />
                      <span>Load in Workspace</span>
                    </button>
                    <button
                      onClick={handleExportJSON}
                      className="flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-bold px-3.5 py-2.5 rounded-full border-2 border-slate-200 transition shadow-2xs"
                      title="Download raw report JSON"
                    >
                      <Download className="w-3.5 h-3.5 text-emerald-600" />
                      <span>JSON</span>
                    </button>
                    <button
                      onClick={handleExportCSV}
                      className="flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-bold px-3.5 py-2.5 rounded-full border-2 border-slate-200 transition shadow-2xs"
                      title="Download item table CSV"
                    >
                      <Download className="w-3.5 h-3.5 text-emerald-600" />
                      <span>CSV</span>
                    </button>
                  </div>
                </div>

                {/* Verdict Banner */}
                {(reportDetail.summary?.asbestos_positive || 0) > 0 ? (
                  <div className="bg-rose-50 border-2 border-rose-300 rounded-2xl p-4.5 flex items-start gap-3 shadow-2xs">
                    <ShieldAlert className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-extrabold text-sm text-rose-800 flex items-center gap-2">
                        HAZARDOUS ASBESTOS MATERIALS IDENTIFIED (石綿含有建材特定)
                        <span className="px-2.5 py-0.5 text-[10px] rounded-full bg-rose-200 text-rose-900 border border-rose-400 font-lab-mono font-bold">
                          {reportDetail.summary?.asbestos_positive || 0} Items
                        </span>
                      </div>
                      <p className="text-xs text-rose-800 mt-1 leading-relaxed font-sans">
                        Mandatory containment and abatement notification required per Japanese Air Pollution Control Act (大気汚染防止法) and Ordinance on Prevention of Asbestos Hazards (石綿障害予防規則).
                      </p>
                      {reportDetail.positive_materials && reportDetail.positive_materials.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2.5">
                          {reportDetail.positive_materials.map((mat, idx) => (
                            <span
                              key={idx}
                              className="text-[11px] px-2.5 py-1 rounded-full bg-white text-rose-800 border-2 border-rose-300 font-bold shadow-2xs"
                            >
                              ⚠ {mat}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-emerald-50 border-2 border-emerald-400 rounded-2xl p-4.5 flex items-start gap-3 shadow-2xs">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-extrabold text-sm text-emerald-900">
                        CERTIFIED NON-ASBESTOS (石綿非含有 認定)
                      </div>
                      <p className="text-xs text-emerald-800 mt-1 font-sans">
                        All materials mapped to post-2006 non-hazardous mineral substitutes (Rockwool, Glasswool, Calcium Silicate Board Type 2) or verified non-asbestos controls.
                      </p>
                    </div>
                  </div>
                )}

                {/* Metrics Breakdown Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-white border-2 border-emerald-300 rounded-2xl p-4 text-center shadow-xs">
                    <div className="text-2xl font-lab-mono font-extrabold text-slate-900">
                      {reportDetail.total_material_annotations || 0}
                    </div>
                    <div className="text-[11px] font-bold text-slate-600 mt-1 uppercase tracking-wider">Total Annotations</div>
                  </div>
                  <div className="bg-rose-50 border-2 border-rose-300 rounded-2xl p-4 text-center shadow-xs">
                    <div className="text-2xl font-lab-mono font-extrabold text-rose-600">
                      {reportDetail.summary?.asbestos_positive || 0}
                    </div>
                    <div className="text-[11px] font-bold text-rose-700 mt-1 uppercase tracking-wider">Asbestos Positive</div>
                  </div>
                  <div className="bg-emerald-50 border-2 border-emerald-400 rounded-2xl p-4 text-center shadow-xs">
                    <div className="text-2xl font-lab-mono font-extrabold text-emerald-700">
                      {reportDetail.summary?.non_asbestos || 0}
                    </div>
                    <div className="text-[11px] font-bold text-emerald-800 mt-1 uppercase tracking-wider">Certified Safe</div>
                  </div>
                  <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-4 text-center shadow-xs">
                    <div className="text-2xl font-lab-mono font-extrabold text-amber-600">
                      {reportDetail.summary?.review_required || reportDetail.summary?.uncertain || 0}
                    </div>
                    <div className="text-[11px] font-bold text-amber-700 mt-1 uppercase tracking-wider">Review Flagged</div>
                  </div>
                </div>

                {/* Level 1 / 2 / 3 Hazard Tiers */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="bg-white border-2 border-rose-200 rounded-2xl p-4 shadow-2xs">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-rose-700">Level 1 (吹付け石綿)</span>
                      <span className="text-xl font-extrabold font-lab-mono text-rose-600">
                        {reportDetail.summary?.hazard_levels?.level_1_sprays || 0}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 font-sans">
                      Sprayed acoustic & fireproofing materials (Most friable & hazardous)
                    </p>
                  </div>
                  <div className="bg-white border-2 border-amber-200 rounded-2xl p-4 shadow-2xs">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-700">Level 2 (保温材・耐火被覆)</span>
                      <span className="text-xl font-extrabold font-lab-mono text-amber-600">
                        {reportDetail.summary?.hazard_levels?.level_2_insulation || 0}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 font-sans">
                      Pipe insulation, boiler lagging, and fire-resistant jackets
                    </p>
                  </div>
                  <div className="bg-white border-2 border-orange-200 rounded-2xl p-4 shadow-2xs">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-orange-700">Level 3 (成形板・スレート)</span>
                      <span className="text-xl font-extrabold font-lab-mono text-orange-600">
                        {reportDetail.summary?.hazard_levels?.level_3_molded || 0}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 font-sans">
                      Corrugated cement slates, vinyl tiles, and calcium silicate boards
                    </p>
                  </div>
                </div>

                {/* Item-by-Item Diagnoses Table */}
                <div className="bg-white border-2 border-emerald-200 rounded-2xl overflow-hidden shadow-sm">
                  <div className="p-4 border-b-2 border-emerald-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-emerald-50/50">
                    <div>
                      <h4 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                        Detailed Item Diagnostics ({filteredReportDiagnoses.length} / {reportDetail.diagnoses?.length || 0})
                      </h4>
                      <p className="text-xs text-slate-600 font-sans">
                        Per-entity MLIT matching, OCR recognition, and regulatory citations
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Search */}
                      <div className="relative">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          value={reportSearchQuery}
                          onChange={(e) => setReportSearchQuery(e.target.value)}
                          placeholder="Search items or materials..."
                          className="bg-white border-2 border-emerald-200 rounded-full pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-48 sm:w-60 shadow-2xs"
                        />
                      </div>

                      {/* Filter */}
                      <select
                        value={reportFilter}
                        onChange={(e) => setReportFilter(e.target.value as any)}
                        className="bg-white border-2 border-emerald-200 rounded-full px-3 py-1.5 text-xs text-slate-800 font-bold focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs"
                      >
                        <option value="ALL">All Items</option>
                        <option value="POSITIVE">Positive Only</option>
                        <option value="NEGATIVE">Safe Only</option>
                        <option value="UNCERTAIN">Review Only</option>
                      </select>
                    </div>
                  </div>

                  <div className="max-h-96 overflow-y-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead className="bg-emerald-100/70 sticky top-0 border-b-2 border-emerald-200 text-emerald-950 font-bold font-lab-mono">
                        <tr>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Raw OCR Text</th>
                          <th className="py-2.5 px-3">Matched MLIT Material</th>
                          <th className="py-2.5 px-3">Confidence</th>
                          <th className="py-2.5 px-3">Hazard Tier</th>
                          <th className="py-2.5 px-3">Citation / Regulation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-lab-mono">
                        {filteredReportDiagnoses.map((item, idx) => (
                          <tr
                            key={idx}
                            className={`hover:bg-emerald-50/60 transition ${
                              item.status === "POSITIVE"
                                ? "bg-rose-50/50"
                                : item.status === "UNCERTAIN"
                                ? "bg-amber-50/50"
                                : ""
                            }`}
                          >
                            <td className="py-2.5 px-3">
                              {item.status === "POSITIVE" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-300">
                                  POSITIVE
                                </span>
                              )}
                              {item.status === "NEGATIVE" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                                  SAFE
                                </span>
                              )}
                              {item.status === "UNCERTAIN" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
                                  REVIEW
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-bold text-slate-900">
                              {item.raw_text}
                            </td>
                            <td className="py-2.5 px-3 text-slate-800 font-sans">
                              <div className="font-bold">{item.matched_material_ja}</div>
                              <div className="text-[10px] text-slate-500 font-sans">
                                {item.matched_material_en}
                              </div>
                            </td>
                            <td className="py-2.5 px-3 text-emerald-700 font-bold">
                              {((item.confidence || 0) * 100).toFixed(1)}%
                            </td>
                            <td className="py-2.5 px-3">
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-bold">
                                {item.hazard_level}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 text-[11px] font-sans max-w-sm truncate" title={item.regulatory_citation}>
                              {item.regulatory_citation || "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Finish Schedule (if present) */}
                {reportDetail.finish_schedule && reportDetail.finish_schedule.length > 0 && (
                  <div className="bg-white border-2 border-emerald-300 rounded-2xl p-4 shadow-sm">
                    <h4 className="text-sm font-extrabold text-slate-900 mb-2.5 flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-emerald-600" />
                      Extracted Room Finish Schedule (特記仕上表)
                    </h4>
                    <div className="max-h-60 overflow-y-auto rounded-xl border border-emerald-200">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead className="bg-emerald-50 text-emerald-950 font-bold sticky top-0 border-b border-emerald-200 font-lab-mono">
                          <tr>
                            <th className="py-2 px-3">Room (部屋)</th>
                            <th className="py-2 px-3">Floor (床)</th>
                            <th className="py-2 px-3">Wall (壁)</th>
                            <th className="py-2 px-3">Ceiling (天井)</th>
                            <th className="py-2 px-3">Remarks (備考)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-sans">
                          {reportDetail.finish_schedule.map((row, idx) => (
                            <tr key={idx} className="hover:bg-emerald-50/40">
                              <td className="py-2 px-3 font-bold text-slate-900">{row.room}</td>
                              <td className="py-2 px-3 text-slate-700">{row.floor || "—"}</td>
                              <td className="py-2 px-3 text-slate-700">{row.wall || "—"}</td>
                              <td className="py-2 px-3 text-slate-700">{row.ceiling || "—"}</td>
                              <td className="py-2 px-3 text-slate-500 font-lab-mono text-[11px]">{row.remarks || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : isReportLoading ? (
              <div className="py-24 text-center text-slate-500 font-lab-mono text-xs flex flex-col items-center gap-2">
                <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
                <span>Loading complete diagnosis report...</span>
              </div>
            ) : (
              /* ARCHIVE LIST OF ALL CHECKED BLUEPRINTS */
              <div className="space-y-4">
                {/* Search & Filter Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border-2 border-emerald-300 shadow-sm">
                  <div className="relative flex-1 max-w-md">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search checked blueprints by filename, ID, or material..."
                      className="w-full bg-[#f8faf8] border-2 border-emerald-200 rounded-full pl-9 pr-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-2xs"
                    />
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap font-lab-mono">
                    <button
                      onClick={() => setStatusFilter("ALL")}
                      className={`px-3.5 py-1.5 text-xs font-bold rounded-full transition ${
                        statusFilter === "ALL"
                          ? "bg-emerald-100 text-emerald-900 border-2 border-emerald-500 shadow-2xs"
                          : "text-slate-600 hover:text-slate-900 bg-white border border-slate-200"
                      }`}
                    >
                      All ({historyList.length})
                    </button>
                    <button
                      onClick={() => setStatusFilter("HAZARDOUS")}
                      className={`px-3.5 py-1.5 text-xs font-bold rounded-full transition ${
                        statusFilter === "HAZARDOUS"
                          ? "bg-rose-100 text-rose-900 border-2 border-rose-500 shadow-2xs"
                          : "text-rose-700 hover:text-rose-900 bg-white border border-rose-200"
                      }`}
                    >
                      Hazardous ({historyList.filter((h) => (h?.summary?.asbestos_positive || 0) > 0).length})
                    </button>
                    <button
                      onClick={() => setStatusFilter("SAFE")}
                      className={`px-3.5 py-1.5 text-xs font-bold rounded-full transition ${
                        statusFilter === "SAFE"
                          ? "bg-emerald-100 text-emerald-900 border-2 border-emerald-500 shadow-2xs"
                          : "text-emerald-700 hover:text-emerald-900 bg-white border border-emerald-200"
                      }`}
                    >
                      Safe ({historyList.filter((h) => (h?.summary?.asbestos_positive || 0) === 0 && (h?.summary?.uncertain || 0) === 0).length})
                    </button>
                    <button
                      onClick={() => setStatusFilter("REVIEW")}
                      className={`px-3.5 py-1.5 text-xs font-bold rounded-full transition ${
                        statusFilter === "REVIEW"
                          ? "bg-amber-100 text-amber-900 border-2 border-amber-500 shadow-2xs"
                          : "text-amber-700 hover:text-amber-900 bg-white border border-amber-200"
                      }`}
                    >
                      Review Flagged ({historyList.filter((h) => (h?.summary?.uncertain || 0) > 0 || (h?.summary?.review_required || 0) > 0).length})
                    </button>
                  </div>
                </div>

                {/* Checked Files List */}
                {isLoading ? (
                  <div className="py-24 text-center text-slate-500 font-lab-mono text-xs flex flex-col items-center gap-2">
                    <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
                    <span>Loading blueprint history database...</span>
                  </div>
                ) : filteredHistory.length === 0 ? (
                  <div className="py-20 text-center bg-white rounded-2xl border-2 border-emerald-200 p-8 shadow-sm">
                    <Database className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                    <h4 className="text-sm font-bold text-slate-800">No analyzed files match the filter</h4>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto font-sans">
                      All newly uploaded or tested blueprints will automatically be stored in this persistent archive with their diagnosis reports.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3">
                    {filteredHistory.map((item) => {
                      const isHazardous = (item?.summary?.asbestos_positive || 0) > 0;
                      return (
                        <div
                          key={item.drawing_id}
                          className="bg-white border-2 border-emerald-200 hover:border-emerald-400 rounded-2xl p-4.5 transition-all shadow-xs hover:shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4"
                        >
                          {/* File Details */}
                          <div className="flex-1">
                            <div className="flex flex-wrap items-center gap-2 mb-1.5">
                              <span className="font-lab-mono text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold">
                                {item.drawing_id}
                              </span>
                              <span className="text-[11px] text-slate-500 flex items-center gap-1 font-lab-mono">
                                <Clock className="w-3 h-3 text-slate-400" />
                                {item.timestamp}
                              </span>
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-bold">
                                {item.document_type || "DRAWING"}
                              </span>
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-lab-mono">
                                {item.page_count || 1} page{(item.page_count || 1) > 1 ? "s" : ""}
                              </span>
                              {item.quality_assessment && (
                                <span
                                  className={`text-[10px] px-2.5 py-0.5 rounded-full border font-lab-mono font-bold ${
                                    item.quality_assessment.intensity_level === 0
                                      ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                                      : item.quality_assessment.intensity_level === 1
                                      ? "bg-cyan-50 text-cyan-800 border-cyan-300"
                                      : "bg-amber-50 text-amber-800 border-amber-300"
                                  }`}
                                  title={item.quality_assessment.recommendation_reason}
                                >
                                  {item.quality_assessment.intensity_level === 0
                                    ? "Level 0 • Pass-through"
                                    : item.quality_assessment.intensity_level === 1
                                    ? "Level 1 • Gentle"
                                    : "Level 2 • Restored"}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3">
                              <h4 className="text-sm font-extrabold text-slate-900 tracking-tight">
                                {item.filename}
                              </h4>
                              {isHazardous ? (
                                <span className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-0.5 rounded-full bg-rose-100 text-rose-800 border-2 border-rose-300">
                                  <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                                  POSITIVE ({item?.summary?.asbestos_positive || 0} hazardous)
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border-2 border-emerald-300">
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                  CERTIFIED SAFE
                                </span>
                              )}
                            </div>

                            {/* Detected Materials Tags */}
                            {item.positive_materials && item.positive_materials.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5 mt-2">
                                <span className="text-[10px] text-slate-500 font-lab-mono font-bold">Detected:</span>
                                {item.positive_materials.slice(0, 5).map((mat, mIdx) => (
                                  <span
                                    key={mIdx}
                                    className="text-[10px] px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-bold"
                                  >
                                    ⚠ {mat}
                                  </span>
                                ))}
                                {item.positive_materials.length > 5 && (
                                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-bold">
                                    +{item.positive_materials.length - 5} more
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Summary Metrics */}
                            <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-600 font-lab-mono">
                              <span>Entities: <strong className="text-slate-900">{item.total_material_annotations || 0}</strong></span>
                              <span>•</span>
                              <span>Safe: <strong className="text-emerald-700">{item?.summary?.non_asbestos || 0}</strong></span>
                              <span>•</span>
                              <span>Review: <strong className="text-amber-700">{item?.summary?.review_required || item?.summary?.uncertain || 0}</strong></span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={() => handleOpenReport(item.drawing_id)}
                              className="btn-hover-shine flex items-center gap-1.5 bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white text-xs font-bold px-3.5 py-2 rounded-full transition shadow-sm active:scale-95"
                            >
                              <FileText className="w-3.5 h-3.5" />
                              <span>View Diagnosis Report</span>
                            </button>

                            <button
                              onClick={() => handleLoadIntoWorkspace(item.drawing_id)}
                              className="flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-bold px-3 py-2 rounded-full border-2 border-slate-200 hover:border-slate-300 transition shadow-2xs"
                              title="Load drawing and inspect in workspace"
                            >
                              <ArrowUpRight className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Load</span>
                            </button>

                            <button
                              onClick={(e) => handleDeleteRecord(item.drawing_id, e)}
                              className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-full transition"
                              title="Delete from history"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )
          ) : (
            /* MLIT REGULATORY DB SPECIFICATIONS TAB (Green + White Clean Theme) */
            <div className="space-y-5">
              {mlitSummary ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-white border-2 border-rose-300 rounded-2xl p-4 text-center shadow-xs">
                      <div className="text-2xl font-lab-mono font-extrabold text-rose-600">
                        {mlitSummary.level_1_friable}
                      </div>
                      <div className="text-[11px] font-bold text-rose-700 mt-1 uppercase tracking-wider">
                        Level 1 (吹付け石綿)
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 font-sans">
                        Extremely Friable
                      </div>
                    </div>

                    <div className="bg-white border-2 border-amber-300 rounded-2xl p-4 text-center shadow-xs">
                      <div className="text-2xl font-lab-mono font-extrabold text-amber-600">
                        {mlitSummary.level_2_insulation}
                      </div>
                      <div className="text-[11px] font-bold text-amber-700 mt-1 uppercase tracking-wider">
                        Level 2 (保温・断熱材)
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 font-sans">
                        Friable Lagging
                      </div>
                    </div>

                    <div className="bg-white border-2 border-orange-300 rounded-2xl p-4 text-center shadow-xs">
                      <div className="text-2xl font-lab-mono font-extrabold text-orange-600">
                        {mlitSummary.level_3_molded}
                      </div>
                      <div className="text-[11px] font-bold text-orange-700 mt-1 uppercase tracking-wider">
                        Level 3 (成形板・スレート)
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 font-sans">
                        Molded Products
                      </div>
                    </div>

                    <div className="bg-white border-2 border-emerald-400 rounded-2xl p-4 text-center shadow-xs">
                      <div className="text-2xl font-lab-mono font-extrabold text-emerald-700">
                        {mlitSummary.non_asbestos_controls}
                      </div>
                      <div className="text-[11px] font-bold text-emerald-800 mt-1 uppercase tracking-wider">
                        Non-Asbestos Controls
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 font-sans">
                        Safe Mineral Fibers
                      </div>
                    </div>
                  </div>

                  <div className="bg-white border-2 border-emerald-300 rounded-2xl p-5 text-xs text-slate-700 shadow-sm space-y-3.5">
                    <h4 className="font-extrabold text-sm text-slate-900 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      MLIT Regulatory Compliance Framework
                    </h4>
                    <p className="text-slate-600 leading-relaxed font-sans">
                      DrawingScan cross-references all recognized Japanese architectural drawing callouts against the Ministry of Land, Infrastructure, Transport and Tourism (MLIT 国土交通省) Asbestos-Containing Building Materials Database (目で見るアスベスト建材).
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-2 font-sans text-xs">
                      <div className="p-4 bg-emerald-50/60 rounded-xl border-2 border-emerald-200">
                        <span className="font-bold text-emerald-900 block mb-1">大気汚染防止法 (Air Pollution Control Act)</span>
                        <p className="text-slate-600 leading-relaxed">
                          Mandates rigorous site inspections, notification before demolition/renovation, and strict emission monitoring for Level 1, 2, and 3 asbestos building materials.
                        </p>
                      </div>
                      <div className="p-4 bg-emerald-50/60 rounded-xl border-2 border-emerald-200">
                        <span className="font-bold text-emerald-900 block mb-1">石綿障害予防規則 (Ordinance on Prevention of Asbestos Hazards)</span>
                        <p className="text-slate-600 leading-relaxed">
                          Requires certified Asbestos Operations Chiefs (石綿作業主任者), wet containment procedures, and worker protective equipment.
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-slate-500 font-lab-mono text-xs">
                  Loading MLIT Knowledge Base stats...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

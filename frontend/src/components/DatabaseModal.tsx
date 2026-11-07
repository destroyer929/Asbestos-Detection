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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-6xl h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header Bar */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base text-white">
                  DrawingScan Database (図面データベース & 診断履歴)
                </h3>
                <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800/60 font-mono">
                  {historyList.length} Checked Files
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Persistent repository of previously analyzed blueprints, historical records, and MLIT diagnosis reports
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={refreshHistory}
              title="Refresh records"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center justify-between px-6 pt-3 bg-slate-950/50 border-b border-slate-800">
          <div className="flex gap-2">
            <button
              onClick={() => {
                setActiveTab("history");
                setSelectedReportId(null);
                setReportDetail(null);
              }}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition border-b-2 ${
                activeTab === "history"
                  ? "text-cyan-300 border-cyan-400 bg-slate-900/80"
                  : "text-slate-400 border-transparent hover:text-slate-200"
              }`}
            >
              <FileSpreadsheet className="w-4 h-4 text-cyan-400" />
              <span>Checked Files & Diagnosis Reports ({historyList.length})</span>
            </button>
            <button
              onClick={() => {
                setActiveTab("mlit_db");
                setSelectedReportId(null);
              }}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition border-b-2 ${
                activeTab === "mlit_db"
                  ? "text-blue-300 border-blue-400 bg-slate-900/80"
                  : "text-slate-400 border-transparent hover:text-slate-200"
              }`}
            >
              <Layers className="w-4 h-4 text-blue-400" />
              <span>MLIT Reference Specifications (国土交通省基準)</span>
            </button>
          </div>

          {selectedReportId && activeTab === "history" && (
            <button
              onClick={() => {
                setSelectedReportId(null);
                setReportDetail(null);
              }}
              className="flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 transition mb-2"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Back to Files List</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-slate-900">
          {activeTab === "history" ? (
            selectedReportId && reportDetail ? (
              /* DETAILED REPORT VIEW FOR A SINGLE FILE */
              <div className="space-y-6">
                {/* Report Header Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                        {reportDetail.drawing_id}
                      </span>
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        Analyzed: {reportDetail.timestamp || "Archived"}
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {reportDetail.document_type || "DRAWING"}
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-white mt-1.5 flex items-center gap-2">
                      {reportDetail.filename}
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      {reportDetail.total_material_annotations || 0} total material annotations identified across {reportDetail.page_count || 1} sheet(s)
                    </p>
                  </div>

                  {/* Actions & Verdict */}
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => handleLoadIntoWorkspace(reportDetail.drawing_id)}
                      className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition shadow-md shadow-blue-600/30 active:scale-95"
                    >
                      <ArrowUpRight className="w-4 h-4" />
                      <span>Load in Workspace</span>
                    </button>
                    <button
                      onClick={handleExportJSON}
                      className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-lg border border-slate-700 transition"
                      title="Download raw report JSON"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>JSON</span>
                    </button>
                    <button
                      onClick={handleExportCSV}
                      className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-lg border border-slate-700 transition"
                      title="Download item table CSV"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>CSV</span>
                    </button>
                  </div>
                </div>

                {/* Verdict Banner */}
                {(reportDetail.summary?.asbestos_positive || 0) > 0 ? (
                  <div className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-4 flex items-start gap-3">
                    <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold text-sm text-rose-300 flex items-center gap-2">
                        HAZARDOUS ASBESTOS MATERIALS IDENTIFIED (石綿含有建材特定)
                        <span className="px-2 py-0.5 text-[10px] rounded-full bg-rose-900 text-rose-200 border border-rose-700 font-mono">
                          {reportDetail.summary?.asbestos_positive || 0} Items
                        </span>
                      </div>
                      <p className="text-xs text-rose-200/80 mt-1 leading-relaxed">
                        Mandatory containment and abatement notification required per Japanese Air Pollution Control Act (大気汚染防止法) and Ordinance on Prevention of Asbestos Hazards (石綿障害予防規則).
                      </p>
                      {reportDetail.positive_materials && reportDetail.positive_materials.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2.5">
                          {reportDetail.positive_materials.map((mat, idx) => (
                            <span
                              key={idx}
                              className="text-[11px] px-2 py-0.5 rounded bg-rose-900/60 text-rose-200 border border-rose-700/60 font-semibold"
                            >
                              ⚠ {mat}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-emerald-950/40 border border-emerald-800/80 rounded-xl p-4 flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold text-sm text-emerald-300">
                        CERTIFIED NON-ASBESTOS (石綿非含有 認定)
                      </div>
                      <p className="text-xs text-emerald-200/80 mt-1">
                        All materials mapped to post-2006 non-hazardous mineral substitutes (Rockwool, Glasswool, Calcium Silicate Board Type 2) or verified non-asbestos controls.
                      </p>
                    </div>
                  </div>
                )}

                {/* Metrics Breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-center">
                    <div className="text-2xl font-mono font-bold text-white">
                      {reportDetail.total_material_annotations || 0}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Total Annotations</div>
                  </div>
                  <div className="bg-rose-950/30 border border-rose-900/50 rounded-xl p-3 text-center">
                    <div className="text-2xl font-mono font-bold text-rose-400">
                      {reportDetail.summary?.asbestos_positive || 0}
                    </div>
                    <div className="text-[11px] text-rose-300 mt-0.5 font-medium">Asbestos Positive</div>
                  </div>
                  <div className="bg-emerald-950/30 border border-emerald-900/50 rounded-xl p-3 text-center">
                    <div className="text-2xl font-mono font-bold text-emerald-400">
                      {reportDetail.summary?.non_asbestos || 0}
                    </div>
                    <div className="text-[11px] text-emerald-300 mt-0.5 font-medium">Certified Safe</div>
                  </div>
                  <div className="bg-amber-950/30 border border-amber-900/50 rounded-xl p-3 text-center">
                    <div className="text-2xl font-mono font-bold text-amber-400">
                      {reportDetail.summary?.review_required || reportDetail.summary?.uncertain || 0}
                    </div>
                    <div className="text-[11px] text-amber-300 mt-0.5 font-medium">Review Flagged</div>
                  </div>
                </div>

                {/* Level 1 / 2 / 3 Hazard Tiers */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="bg-rose-950/20 border border-rose-900/40 rounded-xl p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-rose-300">Level 1 (吹付け石綿)</span>
                      <span className="text-lg font-bold font-mono text-rose-400">
                        {reportDetail.summary?.hazard_levels?.level_1_sprays || 0}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Sprayed acoustic & fireproofing materials (Most friable & hazardous)
                    </p>
                  </div>
                  <div className="bg-amber-950/20 border border-amber-900/40 rounded-xl p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-amber-300">Level 2 (保温材・耐火被覆)</span>
                      <span className="text-lg font-bold font-mono text-amber-400">
                        {reportDetail.summary?.hazard_levels?.level_2_insulation || 0}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Pipe insulation, boiler lagging, and fire-resistant jackets
                    </p>
                  </div>
                  <div className="bg-orange-950/20 border border-orange-900/40 rounded-xl p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-orange-300">Level 3 (成形板・スレート)</span>
                      <span className="text-lg font-bold font-mono text-orange-400">
                        {reportDetail.summary?.hazard_levels?.level_3_molded || 0}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Corrugated cement slates, vinyl tiles, and calcium silicate boards
                    </p>
                  </div>
                </div>

                {/* Item-by-Item Diagnoses Table */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                  <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950">
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Detailed Item Diagnostics ({filteredReportDiagnoses.length} / {reportDetail.diagnoses?.length || 0})
                      </h4>
                      <p className="text-xs text-slate-400">
                        Per-entity MLIT matching, OCR recognition, and regulatory citations
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Search */}
                      <div className="relative">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          value={reportSearchQuery}
                          onChange={(e) => setReportSearchQuery(e.target.value)}
                          placeholder="Search items or materials..."
                          className="bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-48 sm:w-60"
                        />
                      </div>

                      {/* Filter */}
                      <select
                        value={reportFilter}
                        onChange={(e) => setReportFilter(e.target.value as any)}
                        className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
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
                      <thead className="bg-slate-900/90 sticky top-0 border-b border-slate-800 text-slate-400 font-mono">
                        <tr>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Raw OCR Text</th>
                          <th className="py-2.5 px-3">Matched MLIT Material</th>
                          <th className="py-2.5 px-3">Confidence</th>
                          <th className="py-2.5 px-3">Hazard Tier</th>
                          <th className="py-2.5 px-3">Citation / Regulation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {filteredReportDiagnoses.map((item, idx) => (
                          <tr
                            key={idx}
                            className={`hover:bg-slate-800/40 transition ${
                              item.status === "POSITIVE"
                                ? "bg-rose-950/15"
                                : item.status === "UNCERTAIN"
                                ? "bg-amber-950/10"
                                : ""
                            }`}
                          >
                            <td className="py-2.5 px-3">
                              {item.status === "POSITIVE" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-900 text-rose-200 border border-rose-700">
                                  POSITIVE
                                </span>
                              )}
                              {item.status === "NEGATIVE" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                                  SAFE
                                </span>
                              )}
                              {item.status === "UNCERTAIN" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                                  REVIEW
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-white">
                              {item.raw_text}
                            </td>
                            <td className="py-2.5 px-3 text-slate-200">
                              <div>{item.matched_material_ja}</div>
                              <div className="text-[10px] text-slate-400 font-sans">
                                {item.matched_material_en}
                              </div>
                            </td>
                            <td className="py-2.5 px-3 text-cyan-300">
                              {((item.confidence || 0) * 100).toFixed(1)}%
                            </td>
                            <td className="py-2.5 px-3">
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                {item.hazard_level}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-400 font-sans text-[11px] max-w-xs truncate" title={item.regulatory_citation}>
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
                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 shadow-lg">
                    <h4 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-emerald-400" />
                      Extracted Room Finish Schedule (特記仕上表)
                    </h4>
                    <div className="max-h-60 overflow-y-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead className="bg-slate-900/90 sticky top-0 border-b border-slate-800 text-slate-400">
                          <tr>
                            <th className="py-2 px-3">Room (部屋)</th>
                            <th className="py-2 px-3">Floor (床)</th>
                            <th className="py-2 px-3">Wall (壁)</th>
                            <th className="py-2 px-3">Ceiling (天井)</th>
                            <th className="py-2 px-3">Remarks (備考)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 font-sans">
                          {reportDetail.finish_schedule.map((row, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/30">
                              <td className="py-2 px-3 font-semibold text-white">{row.room}</td>
                              <td className="py-2 px-3 text-slate-300">{row.floor || "—"}</td>
                              <td className="py-2 px-3 text-slate-300">{row.wall || "—"}</td>
                              <td className="py-2 px-3 text-slate-300">{row.ceiling || "—"}</td>
                              <td className="py-2 px-3 text-slate-400 text-[11px]">{row.remarks || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : isReportLoading ? (
              <div className="py-24 text-center text-slate-400 font-mono text-xs flex flex-col items-center gap-2">
                <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
                <span>Loading complete diagnosis report...</span>
              </div>
            ) : (
              /* ARCHIVE LIST OF ALL CHECKED BLUEPRINTS */
              <div className="space-y-4">
                {/* Search & Filter Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                  <div className="relative flex-1 max-w-md">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search checked blueprints by filename, ID, or material..."
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    <button
                      onClick={() => setStatusFilter("ALL")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        statusFilter === "ALL"
                          ? "bg-slate-800 text-white border border-slate-600"
                          : "text-slate-400 hover:text-white"
                      }`}
                    >
                      All ({historyList.length})
                    </button>
                    <button
                      onClick={() => setStatusFilter("HAZARDOUS")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        statusFilter === "HAZARDOUS"
                          ? "bg-rose-950 text-rose-300 border border-rose-700"
                          : "text-slate-400 hover:text-rose-400"
                      }`}
                    >
                      Hazardous ({historyList.filter((h) => (h?.summary?.asbestos_positive || 0) > 0).length})
                    </button>
                    <button
                      onClick={() => setStatusFilter("SAFE")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        statusFilter === "SAFE"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                          : "text-slate-400 hover:text-emerald-400"
                      }`}
                    >
                      Safe ({historyList.filter((h) => (h?.summary?.asbestos_positive || 0) === 0 && (h?.summary?.uncertain || 0) === 0).length})
                    </button>
                    <button
                      onClick={() => setStatusFilter("REVIEW")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        statusFilter === "REVIEW"
                          ? "bg-amber-950 text-amber-300 border border-amber-700"
                          : "text-slate-400 hover:text-amber-400"
                      }`}
                    >
                      Review Flagged ({historyList.filter((h) => (h?.summary?.uncertain || 0) > 0 || (h?.summary?.review_required || 0) > 0).length})
                    </button>
                  </div>
                </div>

                {/* Checked Files List */}
                {isLoading ? (
                  <div className="py-24 text-center text-slate-400 font-mono text-xs flex flex-col items-center gap-2">
                    <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
                    <span>Loading blueprint history database...</span>
                  </div>
                ) : filteredHistory.length === 0 ? (
                  <div className="py-20 text-center bg-slate-950 rounded-xl border border-slate-800 p-8">
                    <Database className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                    <h4 className="text-sm font-semibold text-white">No analyzed files match the filter</h4>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
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
                          className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4"
                        >
                          {/* File Details */}
                          <div className="flex-1">
                            <div className="flex flex-wrap items-center gap-2 mb-1.5">
                              <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800/60 font-semibold">
                                {item.drawing_id}
                              </span>
                              <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                                <Clock className="w-3 h-3 text-slate-500" />
                                {item.timestamp}
                              </span>
                              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                {item.document_type || "DRAWING"}
                              </span>
                              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                                {item.page_count || 1} page{(item.page_count || 1) > 1 ? "s" : ""}
                              </span>
                            </div>

                            <div className="flex items-center gap-3">
                              <h4 className="text-sm font-bold text-white tracking-tight">
                                {item.filename}
                              </h4>
                              {isHazardous ? (
                                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-800">
                                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>
                                  POSITIVE ({item?.summary?.asbestos_positive || 0} hazardous)
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                  CERTIFIED SAFE
                                </span>
                              )}
                            </div>

                            {/* Detected Materials Tags */}
                            {item.positive_materials && item.positive_materials.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5 mt-2">
                                <span className="text-[10px] text-slate-400 font-mono">Detected:</span>
                                {item.positive_materials.slice(0, 5).map((mat, mIdx) => (
                                  <span
                                    key={mIdx}
                                    className="text-[10px] px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-900/60 font-medium"
                                  >
                                    {mat}
                                  </span>
                                ))}
                                {item.positive_materials.length > 5 && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                    +{item.positive_materials.length - 5} more
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Summary Metrics */}
                            <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400 font-mono">
                              <span>Entities: <strong className="text-white">{item.total_material_annotations || 0}</strong></span>
                              <span>•</span>
                              <span>Safe: <strong className="text-emerald-400">{item?.summary?.non_asbestos || 0}</strong></span>
                              <span>•</span>
                              <span>Review: <strong className="text-amber-400">{item?.summary?.review_required || item?.summary?.uncertain || 0}</strong></span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={() => handleOpenReport(item.drawing_id)}
                              className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold px-3 py-2 rounded-lg transition shadow-md shadow-cyan-600/20 active:scale-95"
                            >
                              <FileText className="w-4 h-4" />
                              <span>View Diagnosis Report</span>
                            </button>

                            <button
                              onClick={() => handleLoadIntoWorkspace(item.drawing_id)}
                              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-700 hover:border-slate-600 transition"
                              title="Load drawing and inspect in workspace"
                            >
                              <ArrowUpRight className="w-4 h-4 text-blue-400" />
                              <span>Load</span>
                            </button>

                            <button
                              onClick={(e) => handleDeleteRecord(item.drawing_id, e)}
                              className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 rounded-lg transition"
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
            /* MLIT REGULATORY DB SPECIFICATIONS TAB */
            <div className="space-y-5">
              {mlitSummary ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-rose-950/30 border border-rose-800/60 rounded-xl p-3 text-center">
                      <div className="text-2xl font-mono font-bold text-rose-400">
                        {mlitSummary.level_1_friable}
                      </div>
                      <div className="text-[11px] font-semibold text-rose-300 mt-1">
                        Level 1 (吹付け石綿)
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Extremely Friable
                      </div>
                    </div>

                    <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-3 text-center">
                      <div className="text-2xl font-mono font-bold text-amber-400">
                        {mlitSummary.level_2_insulation}
                      </div>
                      <div className="text-[11px] font-semibold text-amber-300 mt-1">
                        Level 2 (保温・断熱材)
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Friable Lagging
                      </div>
                    </div>

                    <div className="bg-orange-950/30 border border-orange-800/60 rounded-xl p-3 text-center">
                      <div className="text-2xl font-mono font-bold text-orange-400">
                        {mlitSummary.level_3_molded}
                      </div>
                      <div className="text-[11px] font-semibold text-orange-300 mt-1">
                        Level 3 (成形板・スレート)
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Molded Products
                      </div>
                    </div>

                    <div className="bg-emerald-950/30 border border-emerald-800/60 rounded-xl p-3 text-center">
                      <div className="text-2xl font-mono font-bold text-emerald-400">
                        {mlitSummary.non_asbestos_controls}
                      </div>
                      <div className="text-[11px] font-semibold text-emerald-300 mt-1">
                        Non-Asbestos Controls
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Safe Mineral Fibers
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 space-y-3">
                    <h4 className="font-bold text-sm text-white flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-cyan-400" />
                      MLIT Regulatory Compliance Framework
                    </h4>
                    <p className="text-slate-400 leading-relaxed">
                      DrawingScan cross-references all recognized Japanese architectural drawing callouts against the Ministry of Land, Infrastructure, Transport and Tourism (MLIT 国土交通省) Asbestos-Containing Building Materials Database (目で見るアスベスト建材).
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 font-mono text-[11px]">
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <span className="font-bold text-cyan-300">大気汚染防止法 (Air Pollution Control Act)</span>
                        <p className="text-slate-400 font-sans mt-1">
                          Mandates rigorous site inspections, notification before demolition/renovation, and strict emission monitoring for Level 1, 2, and 3 asbestos building materials.
                        </p>
                      </div>
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <span className="font-bold text-cyan-300">石綿障害予防規則 (Ordinance on Prevention of Asbestos Hazards)</span>
                        <p className="text-slate-400 font-sans mt-1">
                          Requires certified Asbestos Operations Chiefs (石綿作業主任者), wet containment procedures, and worker protective equipment.
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-slate-400 font-mono text-xs">
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

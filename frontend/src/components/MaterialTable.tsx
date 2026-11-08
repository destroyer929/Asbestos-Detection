"use client";

import React, { useState, useMemo } from "react";
import {
  Search,
  Download,
  Filter,
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  ArrowUpDown,
} from "lucide-react";
import { DiagnosisItem, AsbestosStatus } from "@/types/drawing";

interface MaterialTableProps {
  diagnoses: DiagnosisItem[];
  selectedItem: DiagnosisItem | null;
  onSelectItem: (item: DiagnosisItem) => void;
  activeFilter: AsbestosStatus | "ALL";
  filename: string;
}

export const MaterialTable: React.FC<MaterialTableProps> = ({
  diagnoses,
  selectedItem,
  onSelectItem,
  activeFilter,
  filename,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortField, setSortField] = useState<keyof DiagnosisItem>("item_id");
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  // Filter & Search
  const filteredItems = useMemo(() => {
    return diagnoses.filter((d) => {
      // Status filter
      if (activeFilter !== "ALL" && d.status !== activeFilter) return false;

      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesRaw = d.raw_text.toLowerCase().includes(q);
        const matchesNorm = d.normalized_text.toLowerCase().includes(q);
        const matchesJa = d.matched_material_ja.toLowerCase().includes(q);
        const matchesEn = d.matched_material_en.toLowerCase().includes(q);
        const matchesId = d.item_id.toLowerCase().includes(q);
        return matchesRaw || matchesNorm || matchesJa || matchesEn || matchesId;
      }
      return true;
    });
  }, [diagnoses, activeFilter, searchQuery]);

  // Sort
  const sortedItems = useMemo(() => {
    return [...filteredItems].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortAsc ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });
  }, [filteredItems, sortField, sortAsc]);

  const handleSort = (field: keyof DiagnosisItem) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    const headers = [
      "No.",
      "Item ID",
      "Raw OCR Text",
      "Normalized Text",
      "Status",
      "Hazard Level",
      "Matched Material (JA)",
      "Matched Material (EN)",
      "Match Tier",
      "Confidence",
      "Review Flag",
      "Regulatory Citation",
    ];

    const rows = sortedItems.map((d, index) => [
      `#${index + 1}`,
      d.item_id,
      `"${d.raw_text.replace(/"/g, '""')}"`,
      `"${d.normalized_text.replace(/"/g, '""')}"`,
      d.status,
      d.hazard_level,
      `"${d.matched_material_ja}"`,
      `"${d.matched_material_en}"`,
      d.match_tier,
      `${(d.confidence * 100).toFixed(1)}%`,
      d.requires_human_review ? "REVIEW_REQUIRED" : "OK",
      `"${d.regulatory_citation.replace(/"/g, '""')}"`,
    ]);

    const csvContent = "\uFEFF" + [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `asbestos_audit_${filename || "drawing"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl mt-4">
      {/* Table Toolbar */}
      <div className="p-4 bg-slate-950/70 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="font-bold text-sm text-slate-200">
            Material Inspection Table
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
            {sortedItems.length} of {diagnoses.length} entities
          </span>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search material, room, or text..."
              className="w-full bg-slate-900 text-xs text-slate-200 pl-9 pr-3 py-1.5 rounded-lg border border-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-500"
            />
          </div>

          {/* Export CSV Button */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-700 transition"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-slate-950 text-slate-400 sticky top-0 z-10 select-none">
            <tr className="border-b border-slate-800">
              <th className="py-2.5 px-3 font-semibold w-12">No.</th>
              <th
                onClick={() => handleSort("page_number")}
                className="py-2.5 px-3 font-semibold w-16 cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1">
                  <span>Page</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                onClick={() => handleSort("status")}
                className="py-2.5 px-3 font-semibold cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1">
                  <span>Status</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-2.5 px-3 font-semibold">Raw Text (生OCR)</th>
              <th className="py-2.5 px-3 font-semibold">Matched Material (材料名)</th>
              <th
                onClick={() => handleSort("confidence")}
                className="py-2.5 px-3 font-semibold cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1">
                  <span>Confidence</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-2.5 px-3 font-semibold">Tier</th>
              <th className="py-2.5 px-3 font-semibold">Review Flag</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {sortedItems.map((item, idx) => {
              const isSelected = selectedItem?.item_id === item.item_id;
              const isPos = item.status === "POSITIVE";
              const isNeg = item.status === "NEGATIVE";

              return (
                <tr
                  key={item.item_id}
                  onClick={() => onSelectItem(item)}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-blue-950/50 hover:bg-blue-950/70"
                      : "hover:bg-slate-800/40"
                  }`}
                >
                  <td className="py-2.5 px-3 text-slate-400 font-bold">
                    #{idx + 1}
                  </td>
                  <td className="py-2.5 px-3 text-blue-400 font-semibold">
                    P.{item.page_number || 1}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        isPos
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : isNeg
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                          : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                      }`}
                    >
                      {isPos && <AlertOctagon className="w-3 h-3" />}
                      {isNeg && <CheckCircle2 className="w-3 h-3" />}
                      {!isPos && !isNeg && <AlertTriangle className="w-3 h-3" />}
                      {item.status} [{item.hazard_level.replace("LEVEL_", "L")}]
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-sans text-slate-200 max-w-xs truncate">
                    {item.raw_text}
                  </td>
                  <td className="py-2.5 px-3 font-sans text-slate-300">
                    <span>{item.matched_material_ja}</span>
                    <span className="text-slate-500 text-[11px] ml-1.5 hidden md:inline">
                      ({item.matched_material_en})
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-300">
                    {(item.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                    {item.match_tier === "TIER_5_LLM" ? (
                      <span className="px-1.5 py-0.5 rounded bg-purple-900/50 border border-purple-500/40 text-purple-300 font-bold inline-flex items-center gap-1">
                        <span>🤖</span> T5_LLM
                      </span>
                    ) : (
                      item.match_tier.replace("TIER_", "T")
                    )}
                  </td>
                  <td className="py-2.5 px-3">
                    {item.requires_human_review ? (
                      <span className="text-amber-400 font-bold text-[10px] px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-700/60">
                        ⚠️ REVIEW
                      </span>
                    ) : (
                      <span className="text-emerald-400 text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-700/60">
                        OK
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};


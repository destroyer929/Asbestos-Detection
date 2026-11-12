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
      `"${d.matched_material_ja.replace(/"/g, '""')}"`,
      `"${d.matched_material_en.replace(/"/g, '""')}"`,
      d.match_tier,
      `${(d.confidence * 100).toFixed(1)}%`,
      d.requires_human_review ? "REVIEW" : "CERTIFIED",
      `"${d.regulatory_citation.replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `asbestos_audit_${filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-md mt-5 border-2 border-emerald-300">
      {/* Table Toolbar */}
      <div className="p-4 bg-emerald-50/80 border-b-2 border-emerald-200 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <span className="font-extrabold text-sm text-slate-900 tracking-wide">
            Material Inspection Table
          </span>
          <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-lab-mono font-bold border border-emerald-200">
            {sortedItems.length} of {diagnoses.length} entities
          </span>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-72">
            <Search className="w-3.5 h-3.5 text-emerald-600 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search material, room, or Japanese text..."
              className="w-full bg-white text-xs text-slate-800 pl-9 pr-3.5 py-2 rounded-full border-2 border-emerald-200 focus:outline-none focus:border-emerald-500 placeholder:text-slate-400 shadow-2xs font-sans"
            />
          </div>

          {/* Export CSV Button */}
          <button
            onClick={handleExportCSV}
            className="btn-hover-shine flex items-center gap-1.5 bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white text-xs font-bold px-4 py-2 rounded-full shadow-sm shadow-emerald-500/20 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-emerald-100/70 text-emerald-950 sticky top-0 z-10 select-none font-lab-mono border-b-2 border-emerald-200">
            <tr>
              <th className="py-2.5 px-3.5 font-bold w-14">No.</th>
              <th
                onClick={() => handleSort("page_number")}
                className="py-2.5 px-3.5 font-bold w-16 cursor-pointer hover:text-emerald-700"
              >
                <div className="flex items-center gap-1">
                  <span>Page</span>
                  <ArrowUpDown className="w-3 h-3 text-emerald-600" />
                </div>
              </th>
              <th
                onClick={() => handleSort("status")}
                className="py-2.5 px-3.5 font-bold cursor-pointer hover:text-emerald-700"
              >
                <div className="flex items-center gap-1">
                  <span>Status</span>
                  <ArrowUpDown className="w-3 h-3 text-emerald-600" />
                </div>
              </th>
              <th className="py-2.5 px-3.5 font-bold">Raw OCR Text (生OCR)</th>
              <th className="py-2.5 px-3.5 font-bold">Matched Material (材料名)</th>
              <th
                onClick={() => handleSort("confidence")}
                className="py-2.5 px-3.5 font-bold cursor-pointer hover:text-emerald-700"
              >
                <div className="flex items-center gap-1">
                  <span>Confidence</span>
                  <ArrowUpDown className="w-3 h-3 text-emerald-600" />
                </div>
              </th>
              <th className="py-2.5 px-3.5 font-bold">Tier</th>
              <th className="py-2.5 px-3.5 font-bold">Review Flag</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-lab-mono">
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
                      ? "bg-emerald-100/70 hover:bg-emerald-100 border-l-4 border-emerald-600"
                      : "hover:bg-emerald-50/50"
                  }`}
                >
                  <td className="py-2.5 px-3.5 text-slate-500 font-bold">
                    #{idx + 1}
                  </td>
                  <td className="py-2.5 px-3.5 text-emerald-700 font-bold">
                    P.{item.page_number || 1}
                  </td>
                  <td className="py-2.5 px-3.5">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        isPos
                          ? "bg-rose-50 text-rose-700 border border-rose-300"
                          : isNeg
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-300"
                          : "bg-amber-50 text-amber-800 border border-amber-300"
                      }`}
                    >
                      {isPos && <AlertOctagon className="w-3 h-3" />}
                      {isNeg && <CheckCircle2 className="w-3 h-3" />}
                      {!isPos && !isNeg && <AlertTriangle className="w-3 h-3" />}
                      {item.status} [{item.hazard_level.replace("LEVEL_", "L")}]
                    </span>
                  </td>
                  <td className="py-2.5 px-3.5 font-sans text-slate-900 max-w-xs truncate font-bold">
                    {item.raw_text}
                  </td>
                  <td className="py-2.5 px-3.5 font-sans text-slate-800 font-medium">
                    <span>{item.matched_material_ja}</span>
                    <span className="text-slate-400 text-[11px] ml-1.5 hidden md:inline">
                      ({item.matched_material_en})
                    </span>
                  </td>
                  <td className="py-2.5 px-3.5 text-slate-700 font-semibold">
                    {(item.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3.5 text-slate-600 text-[11px]">
                    {item.match_tier === "TIER_5_LLM" ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-100 border border-purple-300 text-purple-900 font-bold shadow-2xs whitespace-nowrap">
                        <span>🤖</span> T5_LLM
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-bold">
                        {item.match_tier.replace("TIER_", "T")}
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3.5">
                    {item.requires_human_review ? (
                      <span className="inline-flex items-center gap-1.5 text-amber-900 font-bold text-[10px] px-2.5 py-0.5 rounded-full bg-amber-100 border border-amber-300 shadow-2xs whitespace-nowrap">
                        <AlertTriangle className="w-3 h-3 text-amber-600 flex-shrink-0" />
                        <span>REVIEW</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-emerald-900 text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-100 border border-emerald-300 font-bold shadow-2xs whitespace-nowrap">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                        <span>OK</span>
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

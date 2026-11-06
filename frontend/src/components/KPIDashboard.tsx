"use client";

import React from "react";
import {
  FileText,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Layers,
  Component,
} from "lucide-react";
import { SummaryMetrics, AsbestosStatus } from "@/types/drawing";

interface KPIDashboardProps {
  summary: SummaryMetrics | null;
  totalAnnotations: number;
  activeFilter: AsbestosStatus | "ALL";
  onFilterChange: (filter: AsbestosStatus | "ALL") => void;
  documentType: string;
  isVector: boolean;
}

export const KPIDashboard: React.FC<KPIDashboardProps> = ({
  summary,
  totalAnnotations,
  activeFilter,
  onFilterChange,
  documentType,
  isVector,
}) => {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      {/* 1. Total Annotations */}
      <div
        onClick={() => onFilterChange("ALL")}
        className={`cursor-pointer rounded-xl p-4 transition-all border ${
          activeFilter === "ALL"
            ? "bg-slate-800 border-blue-500 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500"
            : "bg-slate-900/80 border-slate-800 hover:border-slate-700"
        }`}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Detected Entities
          </span>
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <FileText className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white font-mono">
            {totalAnnotations}
          </span>
          <span className="text-xs text-slate-400">items</span>
        </div>
        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800">
          <span>{documentType}</span>
          <span className="text-blue-400 font-mono">
            {isVector ? "Vector CAD Stream" : "300 DPI Raster Scan"}
          </span>
        </div>
      </div>

      {/* 2. Asbestos Positive */}
      <div
        onClick={() => onFilterChange("POSITIVE")}
        className={`cursor-pointer rounded-xl p-4 transition-all border ${
          activeFilter === "POSITIVE"
            ? "bg-rose-950/40 border-rose-500 shadow-lg shadow-rose-500/20 ring-1 ring-rose-500"
            : "bg-slate-900/80 border-slate-800 hover:border-rose-900/50"
        }`}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
            Asbestos Positive (石綿陽性)
          </span>
          <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
            <AlertOctagon className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-rose-400 font-mono">
            {summary.asbestos_positive}
          </span>
          <span className="text-xs text-rose-300">hazardous items</span>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-300 pt-2 border-t border-slate-800 font-mono">
          <span className="px-1.5 py-0.5 rounded bg-rose-900/60 border border-rose-700/50 text-rose-200">
            L1: {summary.hazard_levels.level_1_sprays}
          </span>
          <span className="px-1.5 py-0.5 rounded bg-amber-900/60 border border-amber-700/50 text-amber-200">
            L2: {summary.hazard_levels.level_2_insulation}
          </span>
          <span className="px-1.5 py-0.5 rounded bg-orange-900/60 border border-orange-700/50 text-orange-200">
            L3: {summary.hazard_levels.level_3_molded}
          </span>
        </div>
      </div>

      {/* 3. Non-Asbestos Controls */}
      <div
        onClick={() => onFilterChange("NEGATIVE")}
        className={`cursor-pointer rounded-xl p-4 transition-all border ${
          activeFilter === "NEGATIVE"
            ? "bg-emerald-950/40 border-emerald-500 shadow-lg shadow-emerald-500/20 ring-1 ring-emerald-500"
            : "bg-slate-900/80 border-slate-800 hover:border-emerald-900/50"
        }`}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
            Certified Non-Asbestos (安全)
          </span>
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-emerald-400 font-mono">
            {summary.non_asbestos}
          </span>
          <span className="text-xs text-emerald-300">safe materials</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 pt-2 border-t border-slate-800 flex items-center justify-between">
          <span>Rockwool / Glasswool / Gypsum</span>
          <span className="text-emerald-400 font-mono">&lt; 0.1 wt%</span>
        </div>
      </div>

      {/* 4. Review Required / Uncertain */}
      <div
        onClick={() => onFilterChange("UNCERTAIN")}
        className={`cursor-pointer rounded-xl p-4 transition-all border ${
          activeFilter === "UNCERTAIN"
            ? "bg-amber-950/40 border-amber-500 shadow-lg shadow-amber-500/20 ring-1 ring-amber-500"
            : "bg-slate-900/80 border-slate-800 hover:border-amber-900/50"
        }`}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
            Requires Human Review (要確認)
          </span>
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-amber-400 font-mono">
            {summary.review_required}
          </span>
          <span className="text-xs text-amber-300">items flagged</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 pt-2 border-t border-slate-800 flex items-center justify-between">
          <span>Low OCR or ambiguous term</span>
          <span className="text-amber-400 font-medium">Active Learning</span>
        </div>
      </div>
    </div>
  );
};


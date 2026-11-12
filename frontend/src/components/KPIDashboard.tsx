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
  Cpu,
  Sparkles,
  Sliders,
  ShieldCheck,
} from "lucide-react";
import { SummaryMetrics, AsbestosStatus, QualityAssessment } from "@/types/drawing";

interface KPIDashboardProps {
  summary: SummaryMetrics | null;
  totalAnnotations: number;
  activeFilter: AsbestosStatus | "ALL";
  onFilterChange: (filter: AsbestosStatus | "ALL") => void;
  documentType: string;
  isVector: boolean;
  qualityAssessment?: QualityAssessment | null;
}

export const KPIDashboard: React.FC<KPIDashboardProps> = ({
  summary,
  totalAnnotations,
  activeFilter,
  onFilterChange,
  documentType,
  isVector,
  qualityAssessment,
}) => {
  if (!summary) return null;

  return (
    <div className="space-y-3.5 mb-5">
      {/* 4 Core KPI Cards with Green + White Laboratory Polish & Bold Accent Borders */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* 1. Total Annotations */}
        <div
          onClick={() => onFilterChange("ALL")}
          className={`cursor-pointer rounded-2xl p-4.5 transition-all relative overflow-hidden group ${
            activeFilter === "ALL"
              ? "bg-emerald-50/80 border-2 border-emerald-600 shadow-md ring-2 ring-emerald-500/20"
              : "bg-white border-2 border-emerald-300 hover:border-emerald-500 shadow-sm hover:shadow-md"
          }`}
        >
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[11px] font-extrabold text-slate-600 uppercase tracking-wider flex items-center gap-1.5 font-lab-mono">
              <span>DETECTED ENTITIES</span>
              <span className="text-[10px] text-emerald-700 font-bold">| 検出</span>
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-700 border-2 border-emerald-200 group-hover:scale-105 transition shadow-2xs">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 font-lab-mono">
              {totalAnnotations}
            </span>
            <span className="text-xs text-slate-500 font-bold">items</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 pt-2.5 border-t border-slate-100 font-lab-mono">
            <span className="truncate max-w-[120px] font-bold text-slate-700">{documentType}</span>
            <span className="text-emerald-700 font-extrabold">
              {isVector ? "Vector CAD Stream" : "300 DPI Raster Scan"}
            </span>
          </div>
        </div>

        {/* 2. Asbestos Positive */}
        <div
          onClick={() => onFilterChange("POSITIVE")}
          className={`cursor-pointer rounded-2xl p-4.5 transition-all relative overflow-hidden group ${
            activeFilter === "POSITIVE"
              ? "bg-rose-50 border-2 border-rose-600 shadow-md ring-2 ring-rose-500/20"
              : "bg-white border-2 border-rose-300 hover:border-rose-500 shadow-sm hover:shadow-md"
          }`}
        >
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[11px] font-extrabold text-rose-800 uppercase tracking-wider flex items-center gap-1.5 font-lab-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
              <span>ASBESTOS POSITIVE (石綿陽性)</span>
            </span>
            <div className="p-2 rounded-xl bg-rose-50 text-rose-600 border-2 border-rose-200 group-hover:scale-105 transition shadow-2xs">
              <AlertOctagon className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-rose-600 font-lab-mono">
              {summary.asbestos_positive}
            </span>
            <span className="text-xs text-rose-700 font-bold">hazardous items</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 pt-2.5 border-t border-slate-100 flex items-center gap-2 font-lab-mono">
            <span className="flex items-center gap-1 text-rose-600 font-extrabold">
              <Flame className="w-3.5 h-3.5" /> L1: {summary.hazard_levels.level_1_sprays}
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-orange-600 font-extrabold">
              <Layers className="w-3.5 h-3.5" /> L2: {summary.hazard_levels.level_2_insulation}
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-amber-600 font-extrabold">
              <Component className="w-3.5 h-3.5" /> L3: {summary.hazard_levels.level_3_molded}
            </span>
          </div>
        </div>

        {/* 3. Non-Asbestos Certified */}
        <div
          onClick={() => onFilterChange("NEGATIVE")}
          className={`cursor-pointer rounded-2xl p-4.5 transition-all relative overflow-hidden group ${
            activeFilter === "NEGATIVE"
              ? "bg-emerald-50 border-2 border-emerald-600 shadow-md ring-2 ring-emerald-500/20"
              : "bg-white border-2 border-emerald-400 hover:border-emerald-600 shadow-sm hover:shadow-md"
          }`}
        >
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[11px] font-extrabold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5 font-lab-mono">
              <span>CERTIFIED NON-ASBESTOS (安全)</span>
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-700 border-2 border-emerald-200 group-hover:scale-105 transition shadow-2xs">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-700 font-lab-mono">
              {summary.non_asbestos}
            </span>
            <span className="text-xs text-emerald-800 font-bold">safe materials</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 pt-2.5 border-t border-slate-100 flex items-center justify-between font-lab-mono">
            <span className="font-medium text-slate-600">Rockwool / Glasswool / Gypsum</span>
            <span className="text-emerald-700 font-extrabold">&lt; 0.1 wt%</span>
          </div>
        </div>

        {/* 4. Human Review Required */}
        <div
          onClick={() => onFilterChange("UNCERTAIN")}
          className={`cursor-pointer rounded-2xl p-4.5 transition-all relative overflow-hidden group ${
            activeFilter === "UNCERTAIN"
              ? "bg-amber-50 border-2 border-amber-600 shadow-md ring-2 ring-amber-500/20"
              : "bg-white border-2 border-amber-300 hover:border-amber-500 shadow-sm hover:shadow-md"
          }`}
        >
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[11px] font-extrabold text-amber-900 uppercase tracking-wider flex items-center gap-1.5 font-lab-mono">
              <span>REQUIRES HUMAN REVIEW (要確認)</span>
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-700 border-2 border-amber-200 group-hover:scale-105 transition shadow-2xs">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-600 font-lab-mono">
              {summary.review_required}
            </span>
            <span className="text-xs text-amber-800 font-bold">items flagged</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 pt-2.5 border-t border-slate-100 flex items-center justify-between font-lab-mono">
            <span className="font-medium text-slate-600">Low OCR or unique trade term</span>
            <span className="text-amber-700 font-extrabold">Active Learning</span>
          </div>
        </div>
      </div>

      {/* Adaptive Pre-Flight AI Preprocessing Decision Banner */}
      {qualityAssessment && (
        <div
          className={`p-3.5 rounded-2xl border-2 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs shadow-sm transition-all bg-white ${
            qualityAssessment.intensity_level === 0
              ? "border-emerald-300 text-emerald-950"
              : qualityAssessment.intensity_level === 1
              ? "border-teal-300 text-teal-950"
              : "border-amber-300 text-amber-950"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl border-2 ${
                qualityAssessment.intensity_level === 0
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                  : qualityAssessment.intensity_level === 1
                  ? "bg-teal-50 text-teal-700 border-teal-300"
                  : "bg-amber-50 text-amber-700 border-amber-300"
              }`}
            >
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-extrabold tracking-tight text-slate-900">
                  Adaptive Vision Decision:
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full font-lab-mono text-[10px] font-bold uppercase tracking-wider ${
                    qualityAssessment.intensity_level === 0
                      ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                      : qualityAssessment.intensity_level === 1
                      ? "bg-teal-100 text-teal-900 border border-teal-300"
                      : "bg-amber-100 text-amber-900 border border-amber-300"
                  }`}
                >
                  {qualityAssessment.intensity_level === 0
                    ? "Level 0 • Clean Pass-Through (Raw CJK Strokes Preserved)"
                    : qualityAssessment.intensity_level === 1
                    ? "Level 1 • Gentle Enhancement (No Stroke Erosion)"
                    : "Level 2 • Deep Restoration (Sauvola + Illumination Leveling)"}
                </span>
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5 font-sans">
                {qualityAssessment.recommendation_reason}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end md:self-center font-lab-mono text-[11px] bg-emerald-50/70 px-3.5 py-1.5 rounded-full border-2 border-emerald-200 shadow-2xs">
            <span title="Immerkær noise sigma">
              Noise: <b className="text-slate-900 font-bold">{qualityAssessment.noise_sigma}</b>
            </span>
            <span className="text-slate-300">•</span>
            <span title="Detected scanner tilt">
              Skew: <b className="text-slate-900 font-bold">{qualityAssessment.skew_angle}°</b>
            </span>
            <span className="text-slate-300">•</span>
            <span title="Otsu bimodal contrast separation">
              Clarity: <b className="text-emerald-700 font-extrabold">{(qualityAssessment.bimodal_clarity * 100).toFixed(0)}%</b>
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

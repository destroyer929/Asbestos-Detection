"use client";

import React from "react";
import Image from "next/image";
import {
  Upload,
  Table as TableIcon,
  Database,
  History,
  Sparkles,
} from "lucide-react";

interface NavbarProps {
  health: { status: string; gpu_available: boolean; database_entries: number } | null;
  onOpenUpload: () => void;
  onOpenSchedule: () => void;
  onOpenDatabase: () => void;
  onOpenHistory: () => void;
  isLoading: boolean;
  databaseCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  onOpenUpload,
  onOpenSchedule,
  onOpenDatabase,
  onOpenHistory,
  databaseCount,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b-2 border-emerald-200 text-slate-800 shadow-sm">
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Brand & Identity */}
        <div className="flex items-center space-x-3.5">
          <a
            href="https://alfred-lab.in/"
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center justify-center p-2 rounded-2xl bg-gradient-to-br from-emerald-50 to-white border border-emerald-200 shadow-sm hover:border-emerald-400 transition transform hover:scale-105"
            title="Visit Alfred Lab Official Website"
          >
            <div className="relative w-8 h-8 flex items-center justify-center">
              <Image
                src="/brand/bird.png"
                alt="Alfred Logo"
                width={32}
                height={32}
                className="object-contain group-hover:brightness-105 transition filter drop-shadow-sm"
                priority
              />
            </div>
          </a>

          <div>
            <div className="flex items-center space-x-2.5">
              <span className="font-extrabold text-xl tracking-tight text-[#0f291e]">
                ALFRED
              </span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-emerald-100/90 text-emerald-800 border border-emerald-300 shadow-xs flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Asbestos AI 診断</span>
              </span>
              <span className="hidden md:inline-flex text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-mono">
                JIS A 1481 / MLIT
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-lab-mono flex items-center gap-1.5 mt-0.5">
              <span>Japan Labs (Hamamatsu & Fukuoka)</span>
              <span className="text-emerald-500">•</span>
              <span>New Delhi Liaison</span>
              <span className="text-emerald-500 hidden sm:inline">•</span>
              <span className="hidden sm:inline text-emerald-700 font-bold">Precision Diagnostics</span>
            </p>
          </div>
        </div>

        {/* Navigation Actions */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Upload Button — Primary Alfred Green Pill CTA */}
          <button
            onClick={onOpenUpload}
            className="btn-hover-shine flex items-center gap-2 bg-gradient-to-r from-[#28a745] to-[#20923d] hover:from-[#218838] hover:to-[#1e7e34] text-white text-xs font-bold px-4.5 py-2.5 rounded-full shadow-md shadow-emerald-600/20 transition active:scale-95"
          >
            <Upload className="w-3.5 h-3.5" />
            <span className="tracking-wide">Upload Blueprint</span>
          </button>

          {/* Database Button — Clean White Pill with Emerald Trim */}
          <button
            onClick={onOpenDatabase}
            className="flex items-center gap-1.5 bg-white hover:bg-emerald-50/70 text-emerald-800 text-xs font-bold px-4 py-2.5 rounded-full border-2 border-emerald-300 hover:border-emerald-500 transition shadow-xs"
            title="Open Database: History of all checked blueprints & diagnosis reports"
          >
            <Database className="w-3.5 h-3.5 text-emerald-600" />
            <span className="hidden sm:inline">Database</span>
            {databaseCount !== undefined && databaseCount > 0 && (
              <span className="ml-1 px-2 py-0.5 text-[10px] bg-emerald-100 text-emerald-800 rounded-full border border-emerald-300 font-lab-mono font-bold">
                {databaseCount}
              </span>
            )}
          </button>

          {/* Finish Schedule Modal */}
          <button
            onClick={onOpenSchedule}
            className="flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-bold px-3.5 py-2.5 rounded-full border-2 border-slate-200 hover:border-emerald-300 transition shadow-xs"
          >
            <TableIcon className="w-3.5 h-3.5 text-emerald-600" />
            <span className="hidden xl:inline font-sans">仕上表 (Schedule)</span>
          </button>

          {/* Active Learning Audit */}
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-bold px-3.5 py-2.5 rounded-full border-2 border-slate-200 hover:border-emerald-300 transition shadow-xs"
            title="Active Learning Retraining History"
          >
            <History className="w-3.5 h-3.5 text-amber-500" />
            <span className="hidden xl:inline">Overrides</span>
          </button>

          {/* Health & Engine Status Indicator */}
          <div className="pl-2 border-l border-slate-200 flex items-center">
            {health ? (
              <div
                className="flex items-center gap-1.5 text-[11px] bg-emerald-50/90 text-emerald-900 px-3 py-1.5 rounded-full border border-emerald-200 shadow-xs"
                title={`PaddleOCR Active | Database entries: ${health.database_entries} | Engine: ${health.gpu_available ? "CUDA GPU" : "CPU"}`}
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="font-lab-mono text-emerald-800 font-bold">
                  {health.gpu_available ? "CUDA GPU" : "PaddleOCR CPU"}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-[11px] bg-rose-50 text-rose-800 px-3 py-1.5 rounded-full border border-rose-200">
                <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
                <span className="font-medium">Backend Offline</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

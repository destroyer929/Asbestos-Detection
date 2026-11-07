"use client";

import React from "react";
import {
  ShieldAlert,
  Upload,
  Table as TableIcon,
  Database,
  History,
  FolderArchive,
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
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50 shadow-md">
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Title */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <ShieldAlert className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-blue-300 bg-clip-text text-transparent">
                DrawingScan
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-950 text-blue-300 border border-blue-700/60">
                図面スキャン v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Alfred Co., Ltd. • Hamamatsu R&D • MLIT Asbestos AI
            </p>
          </div>
        </div>

        {/* Navigation Actions */}
        <div className="flex items-center space-x-2">
          {/* Upload Button — primary CTA */}
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-2 rounded-md transition shadow shadow-blue-600/30 active:scale-95"
          >
            <Upload className="w-4 h-4" />
            <span>Upload Blueprint</span>
          </button>

          {/* Database Button — stores all previously checked files & diagnosis reports */}
          <button
            onClick={onOpenDatabase}
            className="flex items-center gap-1.5 bg-cyan-950/70 hover:bg-cyan-900/80 text-cyan-200 text-xs font-semibold px-3 py-2 rounded-md border border-cyan-800/80 hover:border-cyan-600 transition shadow shadow-cyan-950/50"
            title="Open Database: History of all checked blueprints & diagnosis reports"
          >
            <Database className="w-4 h-4 text-cyan-400" />
            <span>Database</span>
            {databaseCount !== undefined && databaseCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 text-[10px] bg-cyan-900 text-cyan-300 rounded-full border border-cyan-700 font-mono">
                {databaseCount}
              </span>
            )}
          </button>

          {/* Finish Schedule Modal */}
          <button
            onClick={onOpenSchedule}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-md border border-slate-700 transition"
          >
            <TableIcon className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">特記仕上表 (Schedule)</span>
          </button>

          {/* Active Learning Audit */}
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-md border border-slate-700 transition"
            title="Active Learning Retraining History"
          >
            <History className="w-4 h-4 text-amber-400" />
            <span className="hidden xl:inline">Overrides</span>
          </button>

          {/* Health & Engine Status Indicator */}
          <div className="pl-2 border-l border-slate-800 flex items-center">
            {health ? (
              <div
                className="flex items-center gap-1.5 text-[11px] bg-slate-800/90 text-slate-300 px-2.5 py-1.5 rounded-full border border-slate-700"
                title={`Database entries: ${health.database_entries} | GPU: ${health.gpu_available ? "Active" : "CPU Fallback"}`}
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {health.gpu_available ? "CUDA GPU" : "CPU"}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-[11px] bg-rose-950/60 text-rose-300 px-2.5 py-1.5 rounded-full border border-rose-800/80">
                <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                <span>API Offline</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

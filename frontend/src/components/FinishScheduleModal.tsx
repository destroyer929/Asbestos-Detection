"use client";

import React from "react";
import { X, Table as TableIcon, Layers, FileSpreadsheet } from "lucide-react";
import { FinishScheduleItem } from "@/types/drawing";

interface FinishScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  schedule: FinishScheduleItem[];
  filename: string;
}

export const FinishScheduleModal: React.FC<FinishScheduleModalProps> = ({
  isOpen,
  onClose,
  schedule,
  filename,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <TableIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">
                特記仕上表 (Architectural Finish Schedule)
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                Document: {filename} • {schedule.length} Room Rows Extracted
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Schedule Matrix Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {schedule.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <Layers className="w-12 h-12 mx-auto mb-3 text-slate-600" />
              <p className="text-sm font-semibold text-slate-300">
                No Finish Schedule Grid Detected
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                This document may contain freeform material callout notes rather than a structured tabular finish matrix (*特記仕上表*).
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-950 text-slate-300 font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-3.5 bg-slate-900/80">Room Name (室名)</th>
                    <th className="py-3 px-3.5">Floor Finish (床)</th>
                    <th className="py-3 px-3.5">Wall Finish (壁)</th>
                    <th className="py-3 px-3.5">Ceiling Finish (天井)</th>
                    <th className="py-3 px-3.5">Remarks (備考)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-sans">
                  {schedule.map((row, idx) => {
                    const hasAsbestosRisk =
                      row.wall.includes("吹付") ||
                      row.wall.includes("石綿") ||
                      row.ceiling.includes("石綿") ||
                      row.ceiling.includes("吹付") ||
                      row.floor.includes("Pタイル") ||
                      row.floor.includes("ビニル床");

                    return (
                      <tr
                        key={idx}
                        className={`transition-colors ${
                          hasAsbestosRisk
                            ? "bg-rose-950/20 hover:bg-rose-950/30"
                            : "hover:bg-slate-800/40"
                        }`}
                      >
                        <td className="py-3 px-3.5 font-bold text-slate-200 bg-slate-950/40">
                          {row.room || "—"}
                        </td>
                        <td className="py-3 px-3.5 text-slate-300">
                          {row.floor || "—"}
                        </td>
                        <td className="py-3 px-3.5 text-slate-300">
                          {row.wall || "—"}
                        </td>
                        <td className="py-3 px-3.5 text-slate-300">
                          {row.ceiling || "—"}
                        </td>
                        <td className="py-3 px-3.5 text-slate-400 text-[11px]">
                          {row.remarks || "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Row highlighting indicates suspected asbestos-containing finish materials</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};


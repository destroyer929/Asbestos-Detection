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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-md animate-fadeIn">
      <div className="bg-white border border-emerald-200 rounded-3xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-emerald-50/70 border-b border-emerald-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-white text-emerald-600 border border-emerald-200 shadow-2xs">
              <TableIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-base text-slate-900 tracking-wide">
                特記仕上表 (Architectural Finish Schedule)
              </h3>
              <p className="text-xs text-emerald-800 font-lab-mono">
                Document: {filename} • {schedule.length} Room Rows Extracted
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Schedule Matrix Content */}
        <div className="flex-1 overflow-y-auto p-4 bg-[#f8faf8]">
          {schedule.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <Layers className="w-12 h-12 mx-auto mb-3 text-slate-400" />
              <p className="text-sm font-bold text-slate-800">
                No Finish Schedule Grid Detected
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto font-sans">
                This document may contain freeform material callout notes rather than a structured tabular finish matrix (*特記仕上表*).
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-emerald-200 bg-white shadow-2xs">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-emerald-50 text-emerald-900 font-bold border-b border-emerald-200 font-lab-mono">
                  <tr>
                    <th className="py-3 px-3.5 bg-emerald-100/50">Room Name (室名)</th>
                    <th className="py-3 px-3.5">Floor Finish (床)</th>
                    <th className="py-3 px-3.5">Wall Finish (壁)</th>
                    <th className="py-3 px-3.5">Ceiling Finish (天井)</th>
                    <th className="py-3 px-3.5">Remarks (備考)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {schedule.map((row, idx) => (
                    <tr key={idx} className="hover:bg-emerald-50/50 transition">
                      <td className="py-2.5 px-3.5 font-bold text-slate-900 bg-slate-50/50">
                        {row.room_name || row.room}
                      </td>
                      <td className="py-2.5 px-3.5 text-slate-700">{row.floor || "—"}</td>
                      <td className="py-2.5 px-3.5 text-slate-700">{row.wall || "—"}</td>
                      <td className="py-2.5 px-3.5 text-slate-700">{row.ceiling || "—"}</td>
                      <td className="py-2.5 px-3.5 text-slate-500 font-lab-mono text-[11px]">
                        {row.remarks || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

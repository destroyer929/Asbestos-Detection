"use client";

import React, { useState, useEffect } from "react";
import { X, History, Sparkles, UserCheck } from "lucide-react";
import { ReviewHistoryItem } from "@/types/drawing";
import { fetchReviewHistory } from "@/lib/api";

interface ReviewHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ReviewHistoryModal: React.FC<ReviewHistoryModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [history, setHistory] = useState<ReviewHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchReviewHistory().then((items) => {
        setHistory(items);
        setLoading(false);
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">
                Active Learning Ground-Truth Audit Log
              </h3>
              <p className="text-xs text-slate-400">
                Logged human expert verifications used for continuous model retraining
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="py-12 text-center text-slate-400 font-mono text-xs">
              Loading active learning log...
            </div>
          ) : history.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <UserCheck className="w-12 h-12 mx-auto mb-3 text-slate-600" />
              <p className="text-sm font-semibold text-slate-300">
                No Expert Overrides Recorded Yet
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                When reviewers confirm or override detected entities in the inspector panel, they are saved here to build future fine-tuning datasets.
              </p>
            </div>
          ) : (
            <div className="space-y-3 font-mono text-xs">
              {history.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-blue-400">{item.item_id}</span>
                      <span className="text-[10px] text-slate-500">
                        ({item.drawing_id})
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                          item.corrected_status === "POSITIVE"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            : item.corrected_status === "NEGATIVE"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                        }`}
                      >
                        {item.corrected_status} [{item.corrected_hazard_level}]
                      </span>
                    </div>

                    <p className="font-sans text-xs text-slate-300">
                      Material: {item.corrected_material_name}
                    </p>

                    {item.reviewer_notes && (
                      <p className="font-sans text-[11px] text-slate-400 mt-1 italic">
                        Notes: &quot;{item.reviewer_notes}&quot;
                      </p>
                    )}
                  </div>

                  <div className="text-[10px] text-slate-500 sm:text-right font-mono">
                    {item.timestamp ? new Date(item.timestamp).toLocaleString() : "Just now"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>{history.length} verified ground truth annotations in pool</span>
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


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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-md animate-fadeIn">
      <div className="bg-white border border-emerald-200 rounded-3xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-emerald-50/70 border-b border-emerald-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-white text-amber-600 border border-amber-200 shadow-2xs">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-base text-slate-900 tracking-wide">
                Active Learning Ground-Truth Audit Log
              </h3>
              <p className="text-xs text-slate-500 font-sans">
                Logged human expert verifications used for continuous Alfred MLIT model retraining
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 bg-[#f8faf8]">
          {loading ? (
            <div className="py-12 text-center text-slate-500 font-lab-mono text-xs">
              Loading active learning log...
            </div>
          ) : history.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <UserCheck className="w-12 h-12 mx-auto mb-3 text-slate-400" />
              <p className="text-sm font-bold text-slate-800">
                No Expert Overrides Recorded Yet
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto font-sans">
                When reviewers confirm or override detected entities in the inspector panel, they are saved here to build future fine-tuning datasets.
              </p>
            </div>
          ) : (
            <div className="space-y-3 font-lab-mono text-xs">
              {history.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-white p-3.5 rounded-2xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-slate-900">{item.item_id}</span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          item.corrected_status === "POSITIVE"
                            ? "bg-rose-50 text-rose-700 border border-rose-300"
                            : item.corrected_status === "NEGATIVE"
                            ? "bg-emerald-50 text-emerald-800 border border-emerald-300"
                            : "bg-amber-50 text-amber-800 border border-amber-300"
                        }`}
                      >
                        {item.corrected_status}
                      </span>
                      <span className="text-slate-600 text-[11px] font-sans">
                        {item.corrected_material_name}
                      </span>
                    </div>
                    {item.reviewer_notes && (
                      <p className="text-[11px] text-slate-500 font-sans italic">
                        "{item.reviewer_notes}"
                      </p>
                    )}
                  </div>
                  <div className="text-right text-[11px] text-slate-500">
                    <div>{item.drawing_id}</div>
                    <div className="text-[10px] text-slate-400">{item.timestamp}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

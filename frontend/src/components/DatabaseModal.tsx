"use client";

import React, { useState, useEffect } from "react";
import { X, Database, ShieldCheck, Flame, Layers, Box, Search } from "lucide-react";
import { DatabaseSummary } from "@/types/drawing";
import { fetchDatabaseSummary } from "@/lib/api";

interface DatabaseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DatabaseModal: React.FC<DatabaseModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [summary, setSummary] = useState<DatabaseSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchDatabaseSummary().then((res) => {
        setSummary(res);
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
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">
                MLIT Asbestos Reference Database (国土交通省基準)
              </h3>
              <p className="text-xs text-slate-400">
                Official regulatory classification per 石綿障害予防規則 & 大気汚染防止法
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
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {loading ? (
            <div className="py-12 text-center text-slate-400 font-mono text-xs">
              Loading MLIT Knowledge Base stats...
            </div>
          ) : summary ? (
            <>
              {/* Category Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-rose-950/30 border border-rose-800/60 rounded-xl p-3 text-center">
                  <div className="text-2xl font-mono font-bold text-rose-400">
                    {summary.level_1_friable}
                  </div>
                  <div className="text-[11px] font-semibold text-rose-300 mt-1">
                    Level 1 (吹付け石綿)
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Extremely Friable
                  </div>
                </div>

                <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-3 text-center">
                  <div className="text-2xl font-mono font-bold text-amber-400">
                    {summary.level_2_insulation}
                  </div>
                  <div className="text-[11px] font-semibold text-amber-300 mt-1">
                    Level 2 (保温・断熱材)
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Friable Lagging
                  </div>
                </div>

                <div className="bg-orange-950/30 border border-orange-800/60 rounded-xl p-3 text-center">
                  <div className="text-2xl font-mono font-bold text-orange-400">
                    {summary.level_3_molded}
                  </div>
                  <div className="text-[11px] font-semibold text-orange-300 mt-1">
                    Level 3 (成形板・スレート)
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Molded Products
                  </div>
                </div>

                <div className="bg-emerald-950/30 border border-emerald-800/60 rounded-xl p-3 text-center">
                  <div className="text-2xl font-mono font-bold text-emerald-400">
                    {summary.non_asbestos_controls}
                  </div>
                  <div className="text-[11px] font-semibold text-emerald-300 mt-1">
                    Safe Controls (非石綿)
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    &lt; 0.1 wt% Certified
                  </div>
                </div>
              </div>

              {/* Indexed Search Keys Stat */}
              <div className="p-3.5 bg-slate-950/80 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-300">
                  Total Indexed Search Keys (Synonyms, Full-width & Katakana variants):
                </span>
                <span className="font-mono font-bold text-blue-400 text-sm">
                  {summary.indexed_lookup_keys} keys
                </span>
              </div>

              {/* Regulatory Breakdown Explanations */}
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="font-bold text-rose-400 mb-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                    レベル1 (吹付けアスベスト / 吹付けロックウール)
                  </div>
                  <p className="text-slate-300 leading-relaxed text-[11px]">
                    鉄骨耐火被覆、機械室・ボイラー室天井、吸音断熱材。発じん性が極めて高く、解体・改修時には作業場の隔離、負圧除じん機の設置、労働基準監督署および自治体への工事計画届出が法定義務。
                  </p>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="font-bold text-amber-400 mb-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                    レベル2 (石綿保温材 / けいそう土保温材 / 耐火被覆板)
                  </div>
                  <p className="text-slate-300 leading-relaxed text-[11px]">
                    配管エルボ保温、ボイラー外面保温、煙突断熱材。撤去時に粉じんが飛散しやすいため、隔離養生またはグローブバッグ工法による作業が義務付けられています。
                  </p>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="font-bold text-orange-400 mb-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                    レベル3 (石綿含有成形板 / スレート波板 / ビニル床タイル)
                  </div>
                  <p className="text-slate-300 leading-relaxed text-[11px]">
                    外壁・屋根スレート、フレキシブル板、けい酸カルシウム板第1種、Pタイル。通常状態では飛散しにくいものの、切断・破砕・研磨作業時に発じんするため湿式作業および手ばらし工法が必須。
                  </p>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center text-rose-400 text-xs py-8">
              Failed to load database metrics from backend API.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};


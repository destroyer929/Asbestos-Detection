"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Eye,
  EyeOff,
  Layers,
  Crosshair,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  FileText,
} from "lucide-react";
import { DiagnosisItem, AsbestosStatus, RoomAssessment } from "@/types/drawing";

interface BlueprintCanvasProps {
  imageBase64?: string;
  imageWidth: number;
  imageHeight: number;
  diagnoses: DiagnosisItem[];
  selectedItem: DiagnosisItem | null;
  onSelectItem: (item: DiagnosisItem) => void;
  tableBbox?: [number, number, number, number] | null;
  activeFilter: AsbestosStatus | "ALL";
  currentPage?: number;
  pageCount?: number;
  onPageChange?: (page: number) => void;
  isPageLoading?: boolean;
  roomAssessments?: RoomAssessment[];
}

export const BlueprintCanvas: React.FC<BlueprintCanvasProps> = ({
  imageBase64,
  imageWidth,
  imageHeight,
  diagnoses,
  selectedItem,
  onSelectItem,
  tableBbox,
  activeFilter,
  currentPage = 1,
  pageCount = 1,
  onPageChange,
  isPageLoading = false,
  roomAssessments,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Transform states: zoom and pan offset
  const [scale, setScale] = useState<number>(0.65);
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 20, y: 20 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Overlay toggles
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [showTableGrid, setShowTableGrid] = useState<boolean>(true);
  const [hoveredItem, setHoveredItem] = useState<DiagnosisItem | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);

  // Fit image to container initially or when dimensions change
  const fitToScreen = useCallback(() => {
    if (!containerRef.current || !imageWidth || !imageHeight) return;
    const { clientWidth, clientHeight } = containerRef.current;
    const scaleX = (clientWidth - 40) / imageWidth;
    const scaleY = (clientHeight - 40) / imageHeight;
    const bestScale = Math.min(scaleX, scaleY, 1.0);
    const clampedScale = Math.max(0.2, bestScale);

    setScale(clampedScale);
    setOffset({
      x: Math.max(10, (clientWidth - imageWidth * clampedScale) / 2),
      y: Math.max(10, (clientHeight - imageHeight * clampedScale) / 2),
    });
  }, [imageWidth, imageHeight]);

  useEffect(() => {
    // Small delay lets the container settle before measuring dimensions
    const timer = setTimeout(() => fitToScreen(), 80);
    return () => clearTimeout(timer);
  }, [fitToScreen, imageBase64]);

  // Jump-pan to Finish Schedule table when "Focus Table" is clicked
  const focusTable = useCallback(() => {
    if (!tableBbox || !containerRef.current) return;
    const [tx1, ty1, tx2, ty2] = tableBbox;
    const tableW = tx2 - tx1;
    const tableH = ty2 - ty1;
    const { clientWidth, clientHeight } = containerRef.current;

    // Choose a zoom that fits the table with 20px padding on each side
    const tableScale = Math.min(
      (clientWidth - 40) / tableW,
      (clientHeight - 40) / tableH,
      2.0  // cap at 200% so it doesn't get silly
    );
    const clampedScale = Math.max(0.2, tableScale);

    setScale(clampedScale);
    setOffset({
      x: (clientWidth - tableW * clampedScale) / 2 - tx1 * clampedScale,
      y: (clientHeight - tableH * clampedScale) / 2 - ty1 * clampedScale,
    });
  }, [tableBbox]);

  // Center on selected item when selected from table or inspector
  useEffect(() => {
    if (selectedItem && containerRef.current && imageWidth && imageHeight) {
      const [bx1, by1, bx2, by2] = selectedItem.bbox;
      const boxCenterX = (bx1 + bx2) / 2;
      const boxCenterY = (by1 + by2) / 2;
      const { clientWidth, clientHeight } = containerRef.current;

      setOffset({
        x: clientWidth / 2 - boxCenterX * scale,
        y: clientHeight / 2 - boxCenterY * scale,
      });
    }
  }, [selectedItem, scale, imageWidth, imageHeight]);

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (!containerRef.current) return;

    const zoomFactor = 1.15;
    const newScale = e.deltaY < 0 ? scale * zoomFactor : scale / zoomFactor;
    const clampedScale = Math.min(Math.max(newScale, 0.15), 4.0);

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Zoom centered around cursor position
    const newOffsetX = mouseX - ((mouseX - offset.x) / scale) * clampedScale;
    const newOffsetY = mouseY - ((mouseY - offset.y) / scale) * clampedScale;

    setScale(clampedScale);
    setOffset({ x: newOffsetX, y: newOffsetY });
  };

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left click pans
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Filter diagnoses based on top KPI card selection and current sheet page
  const filteredDiagnoses = diagnoses.filter((d) => {
    // If diagnosis has a page_number and multi-page doc, filter to active page
    if (pageCount > 1 && d.page_number && d.page_number !== currentPage) {
      return false;
    }
    if (activeFilter === "ALL") return true;
    return d.status === activeFilter;
  });

  return (
    <div className="relative w-full h-[540px] lg:h-[620px] xl:h-[680px] bg-[#0b1016] rounded-2xl border-2 border-emerald-400/90 overflow-hidden shadow-xl shadow-emerald-950/15 flex flex-col select-none">
      {/* Top Canvas Toolbar */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-none">
        {/* Left: View Controls */}
        <div className="flex items-center gap-1.5 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-full border-2 border-emerald-300 shadow-md pointer-events-auto">
          <button
            onClick={() => setScale((s) => Math.min(s * 1.2, 4.0))}
            className="p-1.5 rounded-full text-slate-700 hover:text-emerald-800 hover:bg-emerald-50 transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setScale((s) => Math.max(s / 1.2, 0.15))}
            className="p-1.5 rounded-full text-slate-700 hover:text-emerald-800 hover:bg-emerald-50 transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={fitToScreen}
            className="p-1.5 rounded-full text-slate-700 hover:text-emerald-800 hover:bg-emerald-50 transition"
            title="Reset to Fit"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <div className="h-4 w-px bg-slate-200 mx-1"></div>
          <span className="text-xs font-lab-mono font-bold text-emerald-800 px-1">
            {Math.round(scale * 100)}%
          </span>
        </div>

        {/* Center: Multi-Page Navigation Controls (When document has multiple sheets) */}
        {pageCount > 1 && onPageChange && (
          <div className="flex items-center gap-2 bg-white/95 backdrop-blur-md px-3.5 py-1.5 rounded-full border-2 border-emerald-300 shadow-md pointer-events-auto">
            <button
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage <= 1 || isPageLoading}
              className="p-1 rounded-full text-slate-700 hover:text-emerald-800 hover:bg-emerald-50 disabled:opacity-30 disabled:pointer-events-none transition"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <FileText className="w-3.5 h-3.5 text-emerald-600" />
              <span>Page</span>
              <select
                value={currentPage}
                onChange={(e) => onPageChange(Number(e.target.value))}
                disabled={isPageLoading}
                className="bg-emerald-50 text-emerald-800 font-lab-mono text-xs px-2 py-0.5 rounded-full border border-emerald-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-bold"
              >
                {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <span className="text-slate-400 font-normal font-lab-mono">of {pageCount}</span>
            </div>

            <button
              onClick={() => onPageChange(Math.min(pageCount, currentPage + 1))}
              disabled={currentPage >= pageCount || isPageLoading}
              className="p-1 rounded-full text-slate-700 hover:text-emerald-800 hover:bg-emerald-50 disabled:opacity-30 disabled:pointer-events-none transition"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            {isPageLoading && (
              <span className="text-[10px] text-emerald-600 animate-pulse font-lab-mono font-bold">Loading...</span>
            )}
          </div>
        )}

        {/* Right: Layer Overlays */}
        <div className="flex items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-full border-2 border-emerald-300 shadow-md pointer-events-auto">
          <button
            onClick={() => setShowBoxes((v) => !v)}
            className={`flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full transition ${
              showBoxes
                ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {showBoxes ? <Eye className="w-3.5 h-3.5 text-emerald-600" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span className="font-lab-mono">Boxes ({filteredDiagnoses.length})</span>
          </button>

          {tableBbox && (
            <button
              onClick={() => setShowTableGrid((v) => !v)}
              className={`flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full transition ${
                showTableGrid
                  ? "bg-teal-100 text-teal-800 border border-teal-300"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>仕上表 Grid</span>
            </button>
          )}
          {tableBbox && (
            <button
              onClick={focusTable}
              className="flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition"
              title="Zoom & pan to the Finish Schedule table"
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Focus Table</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Interactive Pan/Zoom Canvas Area */}
      <div
        ref={containerRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`w-full h-full relative overflow-hidden bg-[#0a0f15] ${
          isDragging ? "cursor-grabbing" : "cursor-grab"
        }`}
        style={{
          backgroundImage: `
            radial-gradient(circle at 1px 1px, rgba(36,176,91,0.22) 1px, transparent 0)
          `,
          backgroundSize: "24px 24px",
        }}
      >
        {/* Render Layer Container with Pan/Zoom Transform */}
        <div
          className="absolute origin-top-left transition-transform duration-75"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            width: imageWidth || 2000,
            height: imageHeight || 1400,
          }}
        >
          {/* Blueprint Image - Exact 1:1 pixel coordinate matching with SVG overlay */}
          {imageBase64 ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageBase64}
              alt="Architectural Blueprint"
              className="absolute inset-0 w-full h-full block pointer-events-none rounded shadow-[0_0_50px_rgba(0,0,0,0.9)] border border-slate-700/60"
              style={{ imageRendering: "crisp-edges" }}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center border-2 border-dashed border-slate-800 rounded bg-slate-900/40 text-slate-500">
              <span className="font-mono text-sm">Loading Drawing Blueprint...</span>
            </div>
          )}

          {/* SVG Overlay Layer for Vector Precision */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none"
            viewBox={`0 0 ${imageWidth || 2000} ${imageHeight || 1400}`}
          >


            {/* Table Boundary Box */}
            {showTableGrid && tableBbox && (
              <g>
                <rect
                  x={tableBbox[0]}
                  y={tableBbox[1]}
                  width={tableBbox[2] - tableBbox[0]}
                  height={tableBbox[3] - tableBbox[1]}
                  fill="rgba(59, 130, 246, 0.05)"
                  stroke="#3b82f6"
                  strokeWidth="3"
                  strokeDasharray="6 4"
                />
                <rect
                  x={tableBbox[0]}
                  y={tableBbox[1] - 26}
                  width="140"
                  height="26"
                  fill="#3b82f6"
                  rx="3"
                />
                <text
                  x={tableBbox[0] + 8}
                  y={tableBbox[1] - 8}
                  fill="#ffffff"
                  fontSize="13"
                  fontWeight="bold"
                  fontFamily="sans-serif"
                >
                  特記仕上表 GRID
                </text>
              </g>
            )}

            {/* Bounding Box Annotations */}
            {showBoxes &&
              filteredDiagnoses.map((d, index) => {
                const [bx1, by1, bx2, by2] = d.bbox;
                const x = Math.min(bx1, bx2);
                const y = Math.min(by1, by2);
                const width = Math.max(Math.abs(bx2 - bx1), 12);
                const height = Math.max(Math.abs(by2 - by1), 10);
                const isSelected = selectedItem?.item_id === d.item_id;

                let strokeColor = "#f59e0b"; // Amber (Uncertain)
                let fillColor = "rgba(245, 158, 11, 0.28)";
                let badgeBg = "#d97706";

                const isNonArch =
                  d.matched_material_en?.includes("(Non-Architectural Material)") ||
                  d.matched_material_en?.includes("Non-Architectural") ||
                  d.matched_material_en?.includes("Non-Material") ||
                  d.match_tier === "GATE_4";

                if (d.status === "POSITIVE") {
                  strokeColor = "#f43f5e"; // Bold Crimson Rose
                  fillColor = "rgba(244, 63, 94, 0.32)";
                  badgeBg = "#e11d48";
                } else if (isNonArch) {
                  strokeColor = "#2563eb"; // Bold Safe Blue
                  fillColor = "rgba(37, 99, 235, 0.28)";
                  badgeBg = "#1d4ed8";
                } else if (d.status === "NEGATIVE") {
                  strokeColor = "#10b981"; // Bold Emerald Green
                  fillColor = "rgba(16, 185, 129, 0.28)";
                  badgeBg = "#059669";
                }

                if (isSelected) {
                  strokeColor = "#06b6d4"; // Radiant Cyan focus
                  fillColor = "rgba(6, 182, 212, 0.42)";
                  badgeBg = "#0891b2";
                }

                return (
                  <g
                    key={d.item_id}
                    className="pointer-events-auto cursor-pointer group"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectItem(d);
                    }}
                    onMouseEnter={(e) => {
                      setHoveredItem(d);
                      const rect = containerRef.current?.getBoundingClientRect();
                      if (rect) {
                        setHoverPos({
                          x: e.clientX - rect.left,
                          y: e.clientY - rect.top,
                        });
                      }
                    }}
                    onMouseLeave={() => {
                      setHoveredItem(null);
                      setHoverPos(null);
                    }}
                  >
                    {/* Bounding Box Rectangle */}
                    <rect
                      x={x}
                      y={y}
                      width={width}
                      height={height}
                      fill={fillColor}
                      stroke={strokeColor}
                      strokeWidth={isSelected ? 4.5 : 3}
                      rx="2"
                    />

                    {/* Badge Label Tag */}
                    <rect
                      x={x}
                      y={y - 22}
                      width={Math.max(38, 22 + (index + 1).toString().length * 8)}
                      height="20"
                      fill={badgeBg}
                      rx="3"
                    />
                    <text
                      x={x + 5}
                      y={y - 7}
                      fill="#ffffff"
                      fontSize="12"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      #{index + 1}
                    </text>
                  </g>
                );
              })}
          </svg>
        </div>

        {/* Hover Tooltip */}
        {hoveredItem && hoverPos && (() => {
          const isHoverNonArch =
            hoveredItem.matched_material_en?.includes("(Non-Architectural Material)") ||
            hoveredItem.matched_material_en?.includes("Non-Architectural") ||
            hoveredItem.matched_material_en?.includes("Non-Material") ||
            hoveredItem.match_tier === "GATE_4";

          return (
            <div
              className="absolute z-30 pointer-events-none bg-slate-900/95 backdrop-blur-md text-white p-3 rounded-xl border border-slate-700 shadow-2xl max-w-xs transition-opacity duration-150"
              style={{
                left: Math.min(hoverPos.x + 15, (containerRef.current?.clientWidth || 500) - 260),
                top: Math.max(hoverPos.y - 80, 20),
              }}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    hoveredItem.status === "POSITIVE"
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                      : isHoverNonArch
                      ? "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                      : hoveredItem.status === "NEGATIVE"
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                  }`}
                >
                  {isHoverNonArch ? "NEGATIVE • NON_MATERIAL" : `${hoveredItem.status} • ${hoveredItem.hazard_level}`}
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {(hoveredItem.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-100 line-clamp-1">
                {hoveredItem.raw_text}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Matched: {hoveredItem.matched_material_ja} ({hoveredItem.matched_material_en})
              </p>
            </div>
          );
        })()}
      </div>

      {/* Bottom Canvas Status Bar with Dark CAD Engineering Bar */}
      <div className="bg-[#080d12] border-t-2 border-emerald-500/30 px-4 py-2.5 flex items-center justify-between text-xs text-slate-300 font-lab-mono">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.7)]"></span>
            <span className="text-rose-200 font-bold">Asbestos Positive (Harmful - Red)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]"></span>
            <span className="text-emerald-200 font-bold">Non-Asbestos (Safe - Green)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(37,99,235,0.7)]"></span>
            <span className="text-blue-200 font-bold">Non-Architectural (Safe - Blue)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.7)]"></span>
            <span className="text-amber-200 font-bold">Uncertain (Review - Amber)</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-slate-400">
            Canvas: {imageWidth} × {imageHeight} px
          </span>
          <span className="text-emerald-400 font-bold">Click box to inspect</span>
        </div>
      </div>
    </div>
  );
};


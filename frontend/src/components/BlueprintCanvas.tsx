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
    <div className="relative w-full h-[640px] lg:h-[720px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl flex flex-col select-none">
      {/* Top Canvas Toolbar */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-none">
        {/* Left: View Controls */}
        <div className="flex items-center gap-1.5 bg-slate-900/90 backdrop-blur-md px-2.5 py-1.5 rounded-xl border border-slate-700/80 shadow-lg pointer-events-auto">
          <button
            onClick={() => setScale((s) => Math.min(s * 1.2, 4.0))}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setScale((s) => Math.max(s / 1.2, 0.15))}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={fitToScreen}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Reset to Fit"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <div className="h-4 w-px bg-slate-700 mx-1"></div>
          <span className="text-xs font-mono font-semibold text-slate-300 px-1">
            {Math.round(scale * 100)}%
          </span>
        </div>

        {/* Center: Multi-Page Navigation Controls (When document has multiple sheets) */}
        {pageCount > 1 && onPageChange && (
          <div className="flex items-center gap-2 bg-slate-900/95 backdrop-blur-md px-3 py-1.5 rounded-xl border border-blue-500/40 shadow-xl pointer-events-auto">
            <button
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage <= 1 || isPageLoading}
              className="p-1 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none transition"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>Page</span>
              <select
                value={currentPage}
                onChange={(e) => onPageChange(Number(e.target.value))}
                disabled={isPageLoading}
                className="bg-slate-800 text-blue-400 font-mono text-xs px-2 py-0.5 rounded border border-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <span className="text-slate-400 font-normal">of {pageCount}</span>
            </div>

            <button
              onClick={() => onPageChange(Math.min(pageCount, currentPage + 1))}
              disabled={currentPage >= pageCount || isPageLoading}
              className="p-1 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none transition"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            {isPageLoading && (
              <span className="text-[10px] text-blue-400 animate-pulse font-mono">Loading...</span>
            )}
          </div>
        )}

        {/* Right: Layer Overlays */}
        <div className="flex items-center gap-2 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-700/80 shadow-lg pointer-events-auto">
          <button
            onClick={() => setShowBoxes((v) => !v)}
            className={`flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-lg transition ${
              showBoxes
                ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {showBoxes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>Boxes ({filteredDiagnoses.length})</span>
          </button>

          {tableBbox && (
            <button
              onClick={() => setShowTableGrid((v) => !v)}
              className={`flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-lg transition ${
                showTableGrid
                  ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>仕上表 Grid</span>
            </button>
          )}
          {tableBbox && (
            <button
              onClick={focusTable}
              className="flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-lg bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-600/40 transition"
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
        className={`w-full h-full relative overflow-hidden bg-slate-950 ${
          isDragging ? "cursor-grabbing" : "cursor-grab"
        }`}
        style={{
          backgroundImage: `
            radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)
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
              className="absolute inset-0 w-full h-full block pointer-events-none rounded shadow-2xl"
              style={{ imageRendering: "auto", filter: "contrast(1.18) brightness(1.06)" }}
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
                let fillColor = "rgba(245, 158, 11, 0.22)";
                let badgeBg = "#d97706";

                if (d.status === "POSITIVE") {
                  strokeColor = "#ef4444"; // Crimson Red
                  fillColor = "rgba(239, 68, 68, 0.25)";
                  badgeBg = "#dc2626";
                } else if (d.status === "NEGATIVE") {
                  strokeColor = "#10b981"; // Emerald Green
                  fillColor = "rgba(16, 185, 129, 0.20)";
                  badgeBg = "#059669";
                }

                if (isSelected) {
                  strokeColor = "#38bdf8"; // Cyan focus
                  fillColor = "rgba(56, 189, 248, 0.40)";
                  badgeBg = "#0284c7";
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
                      strokeWidth={isSelected ? 4 : 2.5}
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
        {hoveredItem && hoverPos && (
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
                    : hoveredItem.status === "NEGATIVE"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                }`}
              >
                {hoveredItem.status} • {hoveredItem.hazard_level}
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
        )}
      </div>

      {/* Bottom Canvas Status Bar */}
      <div className="bg-slate-900/95 border-t border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-400 font-mono">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <span className="text-slate-300 font-medium">Asbestos Positive (Harmful - Red)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-slate-300 font-medium">Non-Asbestos (Safe - Green)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span className="text-slate-300 font-medium">Uncertain (Review - Amber)</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span>
            Canvas: {imageWidth} × {imageHeight} px
          </span>
          <span>Click box to inspect</span>
        </div>
      </div>
    </div>
  );
};


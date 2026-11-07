export type AsbestosStatus = "POSITIVE" | "NEGATIVE" | "UNCERTAIN";

export type HazardLevel =
  | "LEVEL_1"
  | "LEVEL_2"
  | "LEVEL_3"
  | "NON_ASBESTOS"
  | "UNCERTAIN";

export type MatchTier =
  | "TIER_1_EXACT"
  | "TIER_2_DOMAIN_RULE"
  | "TIER_3_FUZZY"
  | "TIER_4_VECTOR_SEMANTIC"
  | "NONE";

export interface DiagnosisItem {
  item_id: string;
  raw_text: string;
  normalized_text: string;
  bbox: [number, number, number, number]; // [x_min, y_min, x_max, y_max]
  region_type: string;
  room_context: string;
  status: AsbestosStatus;
  hazard_level: HazardLevel;
  matched_material_ja: string;
  matched_material_en: string;
  confidence: number;
  match_tier: MatchTier | string;
  requires_human_review: boolean;
  regulatory_citation: string;
  page_number?: number;
}

export interface FinishScheduleItem {
  room: string;
  floor: string;
  wall: string;
  ceiling: string;
  remarks: string;
}

export interface HazardLevelSummary {
  level_1_sprays: number;
  level_2_insulation: number;
  level_3_molded: number;
}

export interface SummaryMetrics {
  asbestos_positive: number;
  non_asbestos: number;
  uncertain: number;
  review_required: number;
  hazard_levels: HazardLevelSummary;
}

export interface PageInfo {
  page_number: number;
  width: number;
  height: number;
  table_bbox?: [number, number, number, number] | null;
}

export interface RoomAssessment {
  room_id: string;
  room_name_ja: string;
  room_name_en: string;
  priority: "HIGH_PRIORITY" | "CHECK" | "SAFE";
  badge_label: string;
  headline: string;
  detail: string;
  suspect_materials: string[];
  hazard_level: HazardLevel | string;
  room_bbox: [number, number, number, number]; // [x_min, y_min, x_max, y_max]
  callout_anchor: [number, number]; // [x, y] center of room
  callout_box?: [number, number, number, number];
}

export interface DrawingAnalysisResponse {
  drawing_id: string;
  filename: string;
  document_type: string;
  is_vector_pdf: boolean;
  page_count?: number;
  current_page?: number;
  pages?: PageInfo[];
  image_width: number;
  image_height: number;
  image_base64?: string;
  table_bbox?: [number, number, number, number] | null;
  total_material_annotations: number;
  summary: SummaryMetrics;
  finish_schedule: FinishScheduleItem[];
  room_assessments?: RoomAssessment[];
  diagnoses: DiagnosisItem[];
}

export interface BenchmarkSample {
  id: string;
  title: string;
  description: string;
  doc_type: string;
}

export interface HumanOverridePayload {
  item_id: string;
  drawing_id: string;
  corrected_status: AsbestosStatus;
  corrected_hazard_level: HazardLevel;
  corrected_material_name: string;
  reviewer_notes?: string;
}

export interface ReviewHistoryItem extends HumanOverridePayload {
  timestamp?: string;
}

export interface DatabaseSummary {
  total_entries: number;
  level_1_friable: number;
  level_2_insulation: number;
  level_3_molded: number;
  non_asbestos_controls: number;
  indexed_lookup_keys: number;
}


export interface DrawingHistorySummary {
  drawing_id: string;
  filename: string;
  timestamp: string;
  document_type: string;
  is_vector_pdf: boolean;
  page_count: number;
  overall_verdict: string;
  verdict_label: string;
  total_material_annotations: number;
  summary: SummaryMetrics;
  positive_materials: string[];
  has_preview: boolean;
}

export interface DrawingHistoryDetail extends DrawingAnalysisResponse {
  timestamp: string;
  overall_verdict: string;
  verdict_label: string;
  positive_materials: string[];
}

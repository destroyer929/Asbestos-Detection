import {
  DrawingAnalysisResponse,
  BenchmarkSample,
  HumanOverridePayload,
  ReviewHistoryItem,
  DatabaseSummary,
} from "@/types/drawing";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function checkApiHealth(): Promise<{
  status: string;
  gpu_available: boolean;
  database_entries: number;
} | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchDatabaseSummary(): Promise<DatabaseSummary | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/database/summary`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchBenchmarkSamples(): Promise<BenchmarkSample[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/samples`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function analyzeBenchmarkSample(
  sampleId: string
): Promise<DrawingAnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/samples/${sampleId}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return await res.json();
}

export async function analyzeUploadedFile(
  file: File
): Promise<DrawingAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "File analysis failed" }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return await res.json();
}

export async function fetchDrawingPage(
  drawingId: string,
  pageNum: number
): Promise<{
  drawing_id: string;
  page_number: number;
  status: string;
  image_width: number;
  image_height: number;
  table_bbox?: [number, number, number, number] | null;
  image_base64: string;
  diagnoses?: any[];
  finish_schedule?: any[];
  room_assessments?: any[];
  message?: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/v1/drawings/${drawingId}/pages/${pageNum}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Failed to load page ${pageNum}` }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }
  return await res.json();
}

export async function fetchJobStatus(drawingId: string): Promise<{
  drawing_id: string;
  status: string;
  total_pages: number;
  completed_pages: number[];
  completed_count: number;
  progress_percent: number;
  current_status: string;
} | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${drawingId}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function submitHumanOverride(
  payload: HumanOverridePayload
): Promise<{ status: string; message: string; total_active_learning_samples: number }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/review/override`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Override submission failed" }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return await res.json();
}

export async function fetchReviewHistory(): Promise<ReviewHistoryItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/review/history`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.corrections || [];
  } catch {
    return [];
  }
}


import {
  DrawingAnalysisResponse,
  BenchmarkSample,
  HumanOverridePayload,
  ReviewHistoryItem,
  DatabaseSummary,
  DrawingHistorySummary,
  DrawingHistoryDetail,
} from "@/types/drawing";

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
}

export async function checkApiHealth(): Promise<{
  status: string;
  gpu_available: boolean;
  database_entries: number;
} | null> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/health`, {
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
    const res = await fetch(`${getApiBaseUrl()}/api/v1/database/summary`, {
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
    const res = await fetch(`${getApiBaseUrl()}/api/v1/samples`, {
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
  const res = await fetch(`${getApiBaseUrl()}/api/v1/samples/${sampleId}/analyze`, {
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

  const res = await fetch(`${getApiBaseUrl()}/api/v1/analyze`, {
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
  image_width: number;
  image_height: number;
  table_bbox?: [number, number, number, number] | null;
  image_base64: string;
}> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/drawings/${drawingId}/pages/${pageNum}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Failed to load page ${pageNum}` }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }
  return await res.json();
}

export async function submitHumanOverride(
  payload: HumanOverridePayload
): Promise<{ status: string; message: string; total_active_learning_samples: number }> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/review/override`, {
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
    const res = await fetch(`${getApiBaseUrl()}/api/v1/review/history`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.corrections || [];
  } catch {
    return [];
  }
}

export async function fetchDrawingHistory(): Promise<DrawingHistorySummary[]> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/history/drawings`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.drawings || [];
  } catch {
    return [];
  }
}

export async function fetchDrawingHistoryDetail(
  drawingId: string
): Promise<DrawingHistoryDetail> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/history/drawings/${drawingId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch drawing history detail" }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }
  return await res.json();
}

export async function deleteDrawingHistory(
  drawingId: string
): Promise<{ status: string; message: string }> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/history/drawings/${drawingId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to delete record" }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }
  return await res.json();
}

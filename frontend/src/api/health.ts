import type { BasicHealthResponse, DetailedHealthResponse } from "../types/health";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchDetailedHealth(): Promise<DetailedHealthResponse> {
  const response = await fetch(`${API_BASE}/api/v1/health`);
  return parseJson<DetailedHealthResponse>(response);
}

export async function fetchBasicHealth(): Promise<BasicHealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  return parseJson<BasicHealthResponse>(response);
}

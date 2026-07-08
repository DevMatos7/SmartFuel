export type HealthPayload = {
  status: string;
  service: string;
  version: string;
  timestamp?: string;
  database?: string;
  redis?: string;
  minio?: string;
  environment?: string;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<HealthPayload> {
  const response = await fetch(`${API_BASE}/api/v1/health`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<HealthPayload>;
}

export async function fetchRootHealth(): Promise<HealthPayload> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<HealthPayload>;
}

import { apiFetch } from "./client";

export type IngestionDocument = {
  id: string;
  batch_id: string;
  status: string;
  document_type: string;
  original_filename?: string | null;
  sha256: string;
  raw_text?: string | null;
  warnings?: string[];
  human_review_required?: boolean;
  auto_activation_forbidden?: boolean;
};

export async function enableQuoteAiPilot() {
  return apiFetch<{ flag_code: string; enabled: boolean }>("/api/v1/quote-ingestion/flags/enable-pilot", {
    method: "POST",
  });
}

export async function ingestQuoteText(payload: {
  text: string;
  station_id?: string | null;
  source_sender?: string | null;
}) {
  return apiFetch<{ batch: { id: string }; document: IngestionDocument; disclaimer: string }>(
    "/api/v1/quote-ingestion/text",
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function listIngestionDocuments() {
  return apiFetch<{ items: IngestionDocument[] }>("/api/v1/quote-ingestion/documents");
}

export async function listIngestionBatches() {
  return apiFetch<{ items: Array<{ id: string; status: string; total_documents: number }> }>(
    "/api/v1/quote-ingestion/batches",
  );
}

export async function fetchIngestionDocument(id: string) {
  return apiFetch<{
    document: IngestionDocument;
    extraction: {
      document_confidence: string | null;
      warnings: string[];
      structured_output: Record<string, unknown> | null;
      provider: string;
      model: string;
    } | null;
    fields: Array<{
      field_path: string;
      raw_value: string | null;
      confidence: string | null;
      value_origin: string;
      evidence_text: string | null;
    }>;
    matches: Array<{
      entity_type: string;
      raw_value: string;
      status: string;
      matched_entity_id: string | null;
      candidates: Array<{ id: string; name?: string }> | null;
    }>;
    review: { id: string; status: string; corrections: Record<string, unknown> | null } | null;
    draft_link: { quote_id: string } | null;
    human_review_required: boolean;
    auto_activation: boolean;
  }>(`/api/v1/quote-ingestion/documents/${id}`);
}

export async function startIngestionReview(id: string) {
  return apiFetch(`/api/v1/quote-ingestion/documents/${id}/start-review`, { method: "POST" });
}

export async function saveIngestionReview(id: string, corrections: Record<string, unknown>, review_notes?: string) {
  return apiFetch(`/api/v1/quote-ingestion/documents/${id}/review`, {
    method: "PUT",
    body: JSON.stringify({ corrections, review_notes }),
  });
}

export async function approveIngestion(id: string, with_corrections = false) {
  return apiFetch(`/api/v1/quote-ingestion/documents/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ with_corrections }),
  });
}

export async function rejectIngestion(id: string, note?: string) {
  return apiFetch(`/api/v1/quote-ingestion/documents/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function createDraftFromIngestion(
  id: string,
  body: {
    distributor_id?: string;
    station_id?: string;
    payment_term_id?: string;
    product_bindings?: Record<string, string>;
  },
) {
  return apiFetch<{ quote_id: string; quote_status: string; activated: boolean; message: string }>(
    `/api/v1/quote-ingestion/documents/${id}/create-draft`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runQuoteAiEvaluation() {
  return apiFetch<{
    id: string;
    status: string;
    case_count: number;
    passed_count: number;
    failed_count: number;
  }>("/api/v1/quote-ingestion/evaluations/runs", { method: "POST" });
}

export async function fetchQuoteAiAnalyticsSummary() {
  return apiFetch<{
    total_documents: number;
    by_status: Record<string, number>;
    auto_activation: boolean;
  }>("/api/v1/analytics/quote-ingestion/summary");
}

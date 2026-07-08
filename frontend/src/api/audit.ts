import { apiFetch } from "./client";

export type AuditLogItem = {
  id: string;
  organization_id: string | null;
  user_id: string | null;
  entity_type: string;
  entity_id: string | null;
  action: string;
  before_data: Record<string, unknown> | null;
  after_data: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  request_id: string | null;
  created_at: string;
};

export type AuditLogList = {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
};

export type AuditFilters = {
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
};

export async function fetchAuditLogs(filters: AuditFilters = {}) {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return apiFetch<AuditLogList>(`/api/v1/audit-logs?${query.toString()}`);
}

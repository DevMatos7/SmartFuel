import { apiFetch } from "./client";

export type OrganizationBusinessSettings = {
  id: string;
  organization_id: string;
  default_supplier_allowed: boolean;
  default_minimum_volume_liters: string;
  updated_by: string | null;
};

export type OrganizationBusinessSettingsUpdate = {
  default_supplier_allowed?: boolean;
  default_minimum_volume_liters?: number;
};

export async function fetchOrganizationBusinessSettings() {
  return apiFetch<OrganizationBusinessSettings>("/api/v1/organization-business-settings");
}

export async function updateOrganizationBusinessSettings(payload: OrganizationBusinessSettingsUpdate) {
  return apiFetch<OrganizationBusinessSettings>("/api/v1/organization-business-settings", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

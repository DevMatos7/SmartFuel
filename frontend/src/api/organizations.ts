import { apiFetch } from "./client";

export type Organization = {
  id: string;
  name: string;
  corporate_name: string;
  cnpj: string;
  timezone: string;
  active: boolean;
};

export async function fetchOrganization() {
  return apiFetch<Organization>("/api/v1/organizations");
}

export async function updateOrganization(id: string, payload: Partial<Organization>) {
  return apiFetch<Organization>(`/api/v1/organizations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function createOrganization(payload: Omit<Organization, "id">) {
  return apiFetch<Organization>("/api/v1/organizations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

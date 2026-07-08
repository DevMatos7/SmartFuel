export type ServiceStatus = "healthy" | "unhealthy";

export type OverallStatus = "healthy" | "degraded" | "unhealthy";

export type ServiceHealth = {
  status: ServiceStatus;
  response_time_ms?: number;
  message?: string;
};

export type DetailedHealthResponse = {
  status: OverallStatus;
  timestamp: string;
  version: string;
  services: {
    api: ServiceHealth;
    database: ServiceHealth;
    redis: ServiceHealth;
    object_storage: ServiceHealth;
  };
};

export type BasicHealthResponse = {
  status: "ok";
  service: string;
  version: string;
  timestamp: string;
};

export type UiStatus = "loading" | "healthy" | "degraded" | "unavailable";

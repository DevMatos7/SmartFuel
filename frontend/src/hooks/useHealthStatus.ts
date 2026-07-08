import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";

import { fetchDetailedHealth } from "../api/health";
import type { UiStatus } from "../types/health";

export function useHealthStatus() {
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);

  const query = useQuery({
    queryKey: ["health", "detailed"],
    queryFn: async () => {
      const data = await fetchDetailedHealth();
      setLastCheckedAt(new Date());
      return data;
    },
    retry: false,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });

  const uiStatus: UiStatus = useMemo(() => {
    if (query.isLoading || query.isFetching) {
      return "loading";
    }
    if (query.isError || !query.data) {
      return "unavailable";
    }
    if (query.data.status === "healthy") {
      return "healthy";
    }
    if (query.data.status === "degraded") {
      return "degraded";
    }
    return "unavailable";
  }, [query.data, query.isError, query.isFetching, query.isLoading]);

  const verifyAgain = useCallback(() => {
    void query.refetch();
  }, [query]);

  return {
    ...query,
    uiStatus,
    lastCheckedAt,
    verifyAgain,
  };
}

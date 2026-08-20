import { useQuery } from "@tanstack/react-query";

import { api } from "../services/api";
import type { DailyCockpitResponse, WeeklyFunnelResponse } from "../types/cockpit";

const ONE_MINUTE = 60 * 1000;

async function fetchDailyCockpit(): Promise<DailyCockpitResponse> {
  const { data } = await api.get<DailyCockpitResponse>("/api/v1/cockpit/daily");
  return data;
}

async function fetchWeeklyFunnel(): Promise<WeeklyFunnelResponse> {
  const { data } = await api.get<WeeklyFunnelResponse>("/api/v1/cockpit/weekly-funnel");
  return data;
}

export function useDailyCockpit() {
  return useQuery({
    queryKey: ["cockpit", "daily"],
    queryFn: fetchDailyCockpit,
    staleTime: ONE_MINUTE,
    refetchInterval: ONE_MINUTE,
  });
}

export function useWeeklyFunnel() {
  return useQuery({
    queryKey: ["cockpit", "weekly-funnel"],
    queryFn: fetchWeeklyFunnel,
    staleTime: 5 * ONE_MINUTE,
  });
}

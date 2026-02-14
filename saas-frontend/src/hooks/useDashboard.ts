import { useQuery } from "@tanstack/react-query";

import { dashboardService } from "../services/dashboardService";

const FIVE_MINUTES = 5 * 60 * 1000;

export function useExecutiveDashboard() {
  return useQuery({
    queryKey: ["dashboard", "executive"],
    queryFn: dashboardService.executive,
    staleTime: FIVE_MINUTES,
  });
}

export function useMrrDashboard() {
  return useQuery({
    queryKey: ["dashboard", "mrr"],
    queryFn: dashboardService.mrr,
    staleTime: FIVE_MINUTES,
  });
}

export function useChurnDashboard() {
  return useQuery({
    queryKey: ["dashboard", "churn"],
    queryFn: dashboardService.churn,
    staleTime: FIVE_MINUTES,
  });
}

export function useLtvDashboard() {
  return useQuery({
    queryKey: ["dashboard", "ltv"],
    queryFn: dashboardService.ltv,
    staleTime: FIVE_MINUTES,
  });
}

export function useGrowthDashboard() {
  return useQuery({
    queryKey: ["dashboard", "growth"],
    queryFn: dashboardService.growth,
    staleTime: FIVE_MINUTES,
  });
}

export function useOperationalDashboard() {
  return useQuery({
    queryKey: ["dashboard", "operational"],
    queryFn: dashboardService.operational,
    staleTime: FIVE_MINUTES,
  });
}

export function useCommercialDashboard() {
  return useQuery({
    queryKey: ["dashboard", "commercial"],
    queryFn: dashboardService.commercial,
    staleTime: FIVE_MINUTES,
  });
}

export function useFinancialDashboard() {
  return useQuery({
    queryKey: ["dashboard", "financial"],
    queryFn: dashboardService.financial,
    staleTime: FIVE_MINUTES,
  });
}

export function useRetentionDashboard() {
  return useQuery({
    queryKey: ["dashboard", "retention"],
    queryFn: dashboardService.retention,
    staleTime: FIVE_MINUTES,
  });
}

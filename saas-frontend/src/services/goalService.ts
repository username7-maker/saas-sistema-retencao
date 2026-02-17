import { api } from "./api";

export type GoalMetricType = "mrr" | "new_members" | "churn_rate" | "nps_avg" | "active_members";
export type GoalComparator = "gte" | "lte";

export interface Goal {
  id: string;
  gym_id: string;
  name: string;
  metric_type: GoalMetricType;
  comparator: GoalComparator;
  target_value: number;
  period_start: string;
  period_end: string;
  alert_threshold_pct: number;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalProgress {
  goal: Goal;
  current_value: number;
  progress_pct: number;
  status: "achieved" | "on_track" | "at_risk";
  status_message: string;
}

export interface GoalCreateInput {
  name: string;
  metric_type: GoalMetricType;
  comparator: GoalComparator;
  target_value: number;
  period_start: string;
  period_end: string;
  alert_threshold_pct: number;
  is_active?: boolean;
  notes?: string;
}

export const goalService = {
  async list(activeOnly = false): Promise<Goal[]> {
    const { data } = await api.get<Goal[]>("/api/v1/goals", {
      params: { active_only: activeOnly },
    });
    return data;
  },

  async progress(activeOnly = true): Promise<GoalProgress[]> {
    const { data } = await api.get<GoalProgress[]>("/api/v1/goals/progress", {
      params: { active_only: activeOnly },
    });
    return data;
  },

  async create(payload: GoalCreateInput): Promise<Goal> {
    const { data } = await api.post<Goal>("/api/v1/goals", payload);
    return data;
  },

  async delete(goalId: string): Promise<void> {
    await api.delete(`/api/v1/goals/${goalId}`);
  },
};

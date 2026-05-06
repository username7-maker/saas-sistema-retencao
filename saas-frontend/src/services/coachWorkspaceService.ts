import { api } from "./api";
import type { WorkQueueOutcome, WorkQueueSourceType } from "../types";

export type CoachWorkspaceState = "do_now" | "awaiting_outcome" | "done" | "all";
export type CoachWorkspaceShift = "my_shift" | "all" | "overnight" | "morning" | "afternoon" | "evening" | "unassigned";

export interface CoachWorkspaceEvidence {
  label: string;
  value: string;
}

export interface CoachWorkspaceItem {
  source_type: WorkQueueSourceType;
  source_id: string;
  member_id: string | null;
  subject_name: string;
  preferred_shift: string | null;
  lane:
    | "training_delivery"
    | "training_feedback"
    | "reassessment"
    | "assessment_pending"
    | "body_composition_review"
    | "training_adjustment"
    | "technical_attention";
  lane_label: string;
  severity: string;
  state: string;
  next_action_label: string;
  reason: string;
  due_at: string | null;
  visible_from: string | null;
  context_path: string;
  suggested_message: string | null;
  technical_ladder_step: string | null;
  technical_ladder_step_label: string | null;
  evidence: CoachWorkspaceEvidence[];
  allowed_outcomes: WorkQueueOutcome[];
}

export interface CoachWorkspaceSummary {
  total: number;
  do_now: number;
  awaiting_outcome: number;
  done: number;
  overdue: number;
  by_lane: Record<string, number>;
}

export interface CoachWorkspaceResponse {
  items: CoachWorkspaceItem[];
  total: number;
  page: number;
  page_size: number;
  state: CoachWorkspaceState;
  shift: CoachWorkspaceShift;
  summary: CoachWorkspaceSummary;
  generated_at: string;
}

export interface ListCoachWorkspaceParams {
  state?: CoachWorkspaceState;
  shift?: CoachWorkspaceShift;
  page?: number;
  page_size?: number;
}

export const coachWorkspaceService = {
  async getWorkspace(params?: ListCoachWorkspaceParams): Promise<CoachWorkspaceResponse> {
    const { page = 1, page_size = 25, state = "do_now", shift = "my_shift" } = params ?? {};
    const { data } = await api.get<CoachWorkspaceResponse>("/api/v1/coach/workspace", {
      params: { page, page_size, state, shift },
    });
    return data;
  },
};

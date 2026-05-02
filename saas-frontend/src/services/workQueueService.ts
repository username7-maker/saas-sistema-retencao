import { api } from "./api";
import type { PaginatedResponse, WorkQueueActionResult, WorkQueueItem, WorkQueueOutcome } from "../types";

export type WorkQueueListState = "do_now" | "awaiting_outcome" | "done" | "all";
export type WorkQueueShiftFilter = "my_shift" | "all" | "overnight" | "morning" | "afternoon" | "evening" | "unassigned";
export type WorkQueueAssigneeFilter = "mine" | "unassigned" | "all";
export type WorkQueueDomainFilter = "all" | "retention" | "onboarding" | "assessment" | "commercial" | "finance" | "manual";
export type WorkQueueSourceFilter = "all" | "task" | "ai_triage";

export interface ListWorkQueueParams {
  state?: WorkQueueListState;
  shift?: WorkQueueShiftFilter;
  assignee?: WorkQueueAssigneeFilter;
  domain?: WorkQueueDomainFilter;
  source?: WorkQueueSourceFilter;
  page?: number;
  page_size?: number;
}

export interface ExecuteWorkQueuePayload {
  auto_approve?: boolean;
  confirm_approval?: boolean;
  operator_note?: string | null;
}

export interface UpdateWorkQueueOutcomePayload {
  outcome: WorkQueueOutcome;
  note?: string | null;
  scheduled_for?: string | null;
  snooze_preset?: "tomorrow" | "next_week" | "custom" | null;
  contact_channel?: "whatsapp" | "call" | "in_person" | "other" | null;
}

export const workQueueService = {
  async listItems(params?: ListWorkQueueParams): Promise<PaginatedResponse<WorkQueueItem>> {
    const { page = 1, page_size = 25, state = "do_now", shift = "my_shift", assignee = "all", domain = "all", source = "all" } = params ?? {};
    const { data } = await api.get<PaginatedResponse<WorkQueueItem>>("/api/v1/work-queue/items", {
      params: { page, page_size, state, shift, assignee, domain, source },
    });
    return data;
  },

  async getItem(sourceType: WorkQueueItem["source_type"], sourceId: string): Promise<WorkQueueItem> {
    const { data } = await api.get<WorkQueueItem>(`/api/v1/work-queue/items/${sourceType}/${sourceId}`);
    return data;
  },

  async executeItem(
    sourceType: WorkQueueItem["source_type"],
    sourceId: string,
    payload: ExecuteWorkQueuePayload,
  ): Promise<WorkQueueActionResult> {
    const { data } = await api.post<WorkQueueActionResult>(
      `/api/v1/work-queue/items/${sourceType}/${sourceId}/execute`,
      payload,
    );
    return data;
  },

  async updateOutcome(
    sourceType: WorkQueueItem["source_type"],
    sourceId: string,
    payload: UpdateWorkQueueOutcomePayload,
  ): Promise<WorkQueueActionResult> {
    const { data } = await api.patch<WorkQueueActionResult>(
      `/api/v1/work-queue/items/${sourceType}/${sourceId}/outcome`,
      payload,
    );
    return data;
  },
};

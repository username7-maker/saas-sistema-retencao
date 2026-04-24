import { api } from "./api";
import type {
  AITriageApprovalUpdateInput,
  AITriageMetricsSummary,
  AITriageOutcomeUpdateInput,
  AITriageRecommendation,
  AITriageSafeActionInput,
  AITriageSafeActionResult,
  PaginatedResponse,
} from "../types";

interface ListAITriageParams {
  page?: number;
  page_size?: number;
}

export const aiTriageService = {
  async getMetricsSummary(): Promise<AITriageMetricsSummary> {
    const { data } = await api.get<AITriageMetricsSummary>("/api/v1/ai/triage/metrics/summary");
    return data;
  },

  async listItems(params?: ListAITriageParams): Promise<PaginatedResponse<AITriageRecommendation>> {
    const { page = 1, page_size = 100 } = params ?? {};
    const { data } = await api.get<PaginatedResponse<AITriageRecommendation>>("/api/v1/ai/triage/items", {
      params: { page, page_size },
    });
    return data;
  },

  async getItem(recommendationId: string): Promise<AITriageRecommendation> {
    const { data } = await api.get<AITriageRecommendation>(`/api/v1/ai/triage/items/${recommendationId}`);
    return data;
  },

  async updateApproval(recommendationId: string, payload: AITriageApprovalUpdateInput): Promise<AITriageRecommendation> {
    const { data } = await api.patch<AITriageRecommendation>(
      `/api/v1/ai/triage/items/${recommendationId}/approval`,
      payload,
    );
    return data;
  },

  async prepareAction(recommendationId: string, payload: AITriageSafeActionInput): Promise<AITriageSafeActionResult> {
    const { data } = await api.post<AITriageSafeActionResult>(
      `/api/v1/ai/triage/items/${recommendationId}/actions/prepare`,
      payload,
    );
    return data;
  },

  async updateOutcome(recommendationId: string, payload: AITriageOutcomeUpdateInput): Promise<AITriageRecommendation> {
    const { data } = await api.patch<AITriageRecommendation>(
      `/api/v1/ai/triage/items/${recommendationId}/outcome`,
      payload,
    );
    return data;
  },
};

import { api } from "./api";
import type { AiReviewCenterActionResult, AiReviewCenterList, AiReviewCenterMetrics } from "../types";

export interface AiReviewCenterListParams {
  source?: string;
  status?: string;
  q?: string;
  limit?: number;
}

export interface AiReviewCenterFeedbackInput {
  decision: "approved" | "edited" | "rejected" | "escalated";
  reason?: string;
  edited_reply?: string;
}

export const aiReviewCenterService = {
  async listItems(params?: AiReviewCenterListParams): Promise<AiReviewCenterList> {
    const { data } = await api.get<AiReviewCenterList>("/api/v1/ai/review-center/items", { params });
    return data;
  },

  async getMetrics(params?: Pick<AiReviewCenterListParams, "source" | "status">): Promise<AiReviewCenterMetrics> {
    const { data } = await api.get<AiReviewCenterMetrics>("/api/v1/ai/review-center/metrics", { params });
    return data;
  },

  async prepareKommo(sourceType: string, sourceId: string): Promise<AiReviewCenterActionResult> {
    const { data } = await api.post<AiReviewCenterActionResult>(
      `/api/v1/ai/review-center/items/${sourceType}/${sourceId}/prepare-kommo`,
    );
    return data;
  },

  async reject(sourceType: string, sourceId: string, reason: string): Promise<AiReviewCenterActionResult> {
    const { data } = await api.post<AiReviewCenterActionResult>(
      `/api/v1/ai/review-center/items/${sourceType}/${sourceId}/reject`,
      { reason },
    );
    return data;
  },

  async recordFeedback(sourceType: string, sourceId: string, payload: AiReviewCenterFeedbackInput): Promise<AiReviewCenterActionResult> {
    const { data } = await api.post<AiReviewCenterActionResult>(
      `/api/v1/ai/review-center/items/${sourceType}/${sourceId}/feedback`,
      payload,
    );
    return data;
  },
};

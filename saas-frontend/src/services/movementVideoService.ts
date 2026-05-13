import { api } from "./api";
import type {
  MovementVideoAiSettings,
  MovementVideoAnalyzeInput,
  MovementVideoApproveInput,
  MovementVideoKommoPrepareResult,
  MovementVideoRejectInput,
  MovementVideoReview,
  MovementVideoReviewCreate,
} from "../types";

export const movementVideoService = {
  async getSettings(): Promise<MovementVideoAiSettings> {
    const { data } = await api.get<MovementVideoAiSettings>("/api/v1/settings/movement-video-ai");
    return data;
  },

  async updateSettings(payload: Partial<MovementVideoAiSettings>): Promise<MovementVideoAiSettings> {
    const { data } = await api.put<MovementVideoAiSettings>("/api/v1/settings/movement-video-ai", payload);
    return data;
  },

  async listReviews(memberId: string): Promise<MovementVideoReview[]> {
    const { data } = await api.get<MovementVideoReview[]>(`/api/v1/members/${memberId}/movement-video/reviews`);
    return data;
  },

  async createReview(memberId: string, payload: MovementVideoReviewCreate): Promise<MovementVideoReview> {
    const { data } = await api.post<MovementVideoReview>(`/api/v1/members/${memberId}/movement-video/reviews`, payload);
    return data;
  },

  async analyzeReview(reviewId: string, payload?: MovementVideoAnalyzeInput): Promise<MovementVideoReview> {
    const { data } = await api.post<MovementVideoReview>(`/api/v1/movement-video/reviews/${reviewId}/analyze`, payload ?? {});
    return data;
  },

  async approveReview(reviewId: string, payload: MovementVideoApproveInput): Promise<MovementVideoReview> {
    const { data } = await api.post<MovementVideoReview>(`/api/v1/movement-video/reviews/${reviewId}/approve`, payload);
    return data;
  },

  async rejectReview(reviewId: string, payload: MovementVideoRejectInput): Promise<MovementVideoReview> {
    const { data } = await api.post<MovementVideoReview>(`/api/v1/movement-video/reviews/${reviewId}/reject`, payload);
    return data;
  },

  async prepareKommo(reviewId: string): Promise<MovementVideoKommoPrepareResult> {
    const { data } = await api.post<MovementVideoKommoPrepareResult>(`/api/v1/movement-video/reviews/${reviewId}/prepare-kommo`);
    return data;
  },
};

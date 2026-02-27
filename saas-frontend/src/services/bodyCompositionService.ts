import type { BodyCompositionEvaluation, BodyCompositionEvaluationCreate } from "../types";
import { api } from "./api";

export const bodyCompositionService = {
  async list(memberId: string, limit = 20): Promise<BodyCompositionEvaluation[]> {
    const { data } = await api.get<BodyCompositionEvaluation[]>(
      `/api/v1/members/${memberId}/body-composition`,
      { params: { limit } },
    );
    return data;
  },

  async create(
    memberId: string,
    payload: BodyCompositionEvaluationCreate,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.post<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition`,
      payload,
    );
    return data;
  },
};

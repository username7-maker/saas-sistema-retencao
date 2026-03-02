import { api } from "./api";

export interface NpsResponse {
  id: string;
  member_id: string | null;
  score: number;
  comment: string | null;
  sentiment: string;
  sentiment_summary: string | null;
  trigger: string;
  response_date: string;
}

export interface NpsEvolutionPoint {
  month: string;
  average_score: number;
  responses: number;
}

export interface NpsResponseCreate {
  member_id?: string;
  score: number;
  comment?: string;
  trigger: string;
}

export const npsService = {
  async evolution(months = 12): Promise<NpsEvolutionPoint[]> {
    const { data } = await api.get<NpsEvolutionPoint[]>("/api/v1/nps/evolution", {
      params: { months },
    });
    return data;
  },

  async detractors(days = 30): Promise<NpsResponse[]> {
    const { data } = await api.get<NpsResponse[]>("/api/v1/nps/detractors", {
      params: { days },
    });
    return data;
  },

  async dispatch(): Promise<Record<string, number>> {
    const { data } = await api.post<Record<string, number>>("/api/v1/nps/dispatch");
    return data;
  },

  async createResponse(payload: NpsResponseCreate): Promise<NpsResponse> {
    const { data } = await api.post<NpsResponse>("/api/v1/nps/responses", payload);
    return data;
  },
};

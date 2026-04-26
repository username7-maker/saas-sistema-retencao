import { api } from "./api";
import type { FinancialEntry, FinancialEntryPayload, PaginatedResponse } from "../types";

export interface FinancialEntryListParams {
  page?: number;
  page_size?: number;
  entry_type?: string;
  status?: string;
  from_date?: string;
  to_date?: string;
}

export const financeService = {
  async listEntries(params?: FinancialEntryListParams): Promise<PaginatedResponse<FinancialEntry>> {
    const { data } = await api.get<PaginatedResponse<FinancialEntry>>("/api/v1/finance/entries", { params });
    return data;
  },

  async createEntry(payload: FinancialEntryPayload): Promise<FinancialEntry> {
    const { data } = await api.post<FinancialEntry>("/api/v1/finance/entries", payload);
    return data;
  },

  async updateEntry(entryId: string, payload: Partial<FinancialEntryPayload>): Promise<FinancialEntry> {
    const { data } = await api.patch<FinancialEntry>(`/api/v1/finance/entries/${entryId}`, payload);
    return data;
  },

  async deleteEntry(entryId: string): Promise<void> {
    await api.delete(`/api/v1/finance/entries/${entryId}`);
  },
};

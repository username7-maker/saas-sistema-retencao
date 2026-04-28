import { api } from "./api";
import type {
  DelinquencyItem,
  DelinquencyMaterializeResult,
  DelinquencySummary,
  FinancialEntry,
  FinancialEntryPayload,
  PaginatedResponse,
} from "../types";

export interface FinancialEntryListParams {
  page?: number;
  page_size?: number;
  entry_type?: string;
  status?: string;
  from_date?: string;
  to_date?: string;
}

export interface DelinquencyItemListParams {
  page?: number;
  page_size?: number;
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

  async getDelinquencySummary(): Promise<DelinquencySummary> {
    const { data } = await api.get<DelinquencySummary>("/api/v1/finance/delinquency/summary");
    return data;
  },

  async listDelinquencyItems(params?: DelinquencyItemListParams): Promise<PaginatedResponse<DelinquencyItem>> {
    const { data } = await api.get<PaginatedResponse<DelinquencyItem>>("/api/v1/finance/delinquency/items", { params });
    return data;
  },

  async materializeDelinquencyTasks(): Promise<DelinquencyMaterializeResult> {
    const { data } = await api.post<DelinquencyMaterializeResult>("/api/v1/finance/delinquency/materialize-tasks");
    return data;
  },
};

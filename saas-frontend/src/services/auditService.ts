import { api } from "./api";

export interface AuditLog {
  id: string;
  action: string;
  entity: string;
  entity_id: string | null;
  created_at: string;
  details: Record<string, unknown>;
}

export const auditService = {
  async listLogs(limit = 100): Promise<AuditLog[]> {
    const { data } = await api.get<AuditLog[]>("/api/v1/audit/logs", {
      params: { limit },
    });
    return data;
  },
};

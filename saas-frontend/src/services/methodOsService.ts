import { api } from "./api";
import type {
  ClientMethodConfig,
  CordexClient,
  MethodActionCreate,
  MethodClientProfile,
  MethodDashboard,
  MethodHumanAction,
  MethodOperationalEvent,
  MethodOperationalEventCreate,
  MethodOperationalTask,
  MethodOutcome,
  MethodOutcomeCreate,
  MethodPerson,
  MethodPersonCreate,
  MethodSegment,
  MethodSegmentPlaybook,
  MethodWeeklyReport,
} from "../types";

export interface MethodClientUpdatePayload {
  name?: string;
  segment_id?: string | null;
  status?: string | null;
  city?: string | null;
  state?: string | null;
  main_contact_name?: string | null;
  main_contact_phone?: string | null;
  main_contact_email?: string | null;
}

export interface MethodConfigUpdatePayload {
  segment_id?: string | null;
  active_pillars?: Record<string, boolean>;
  entry_pillar?: string;
  toolkit?: Record<string, unknown>;
  baseline?: Record<string, unknown>;
  success_criteria?: Record<string, unknown>;
  cadence?: Record<string, unknown>;
}

export interface MethodWeeklyReportRequest {
  period_start?: string | null;
  period_end?: string | null;
}

export const methodOsService = {
  async listSegments(): Promise<MethodSegment[]> {
    const { data } = await api.get<MethodSegment[]>("/api/v1/method-os/segments");
    return data;
  },

  async getSegmentPlaybook(segmentKey: string): Promise<MethodSegmentPlaybook> {
    const { data } = await api.get<MethodSegmentPlaybook>(`/api/v1/method-os/segments/${segmentKey}/playbook`);
    return data;
  },

  async getClientProfile(): Promise<MethodClientProfile> {
    const { data } = await api.get<MethodClientProfile>("/api/v1/method-os/client");
    return data;
  },

  async updateClient(payload: MethodClientUpdatePayload): Promise<CordexClient> {
    const { data } = await api.patch<CordexClient>("/api/v1/method-os/client", payload);
    return data;
  },

  async updateClientConfig(payload: MethodConfigUpdatePayload): Promise<ClientMethodConfig> {
    const { data } = await api.patch<ClientMethodConfig>("/api/v1/method-os/client/config", payload);
    return data;
  },

  async copyPlaybookToClient(segmentId: string): Promise<ClientMethodConfig> {
    const { data } = await api.post<ClientMethodConfig>(`/api/v1/method-os/segments/${segmentId}/copy-to-client`);
    return data;
  },

  async listPeople(): Promise<MethodPerson[]> {
    const { data } = await api.get<MethodPerson[]>("/api/v1/method-os/people", { params: { limit: 100 } });
    return data;
  },

  async createPerson(payload: MethodPersonCreate): Promise<MethodPerson> {
    const { data } = await api.post<MethodPerson>("/api/v1/method-os/people", payload);
    return data;
  },

  async createEvent(payload: MethodOperationalEventCreate): Promise<MethodOperationalEvent> {
    const { data } = await api.post<MethodOperationalEvent>("/api/v1/method-os/events", payload);
    return data;
  },

  async generateTaskFromEvent(eventId: string): Promise<MethodOperationalTask> {
    const { data } = await api.post<MethodOperationalTask>(`/api/v1/method-os/events/${eventId}/tasks`);
    return data;
  },

  async listTasks(status?: string): Promise<MethodOperationalTask[]> {
    const { data } = await api.get<MethodOperationalTask[]>("/api/v1/method-os/tasks", {
      params: { limit: 100, status },
    });
    return data;
  },

  async updateTaskMessage(taskId: string, suggestedMessage: string | null): Promise<MethodOperationalTask> {
    const { data } = await api.patch<MethodOperationalTask>(`/api/v1/method-os/tasks/${taskId}/message`, {
      suggested_message: suggestedMessage,
    });
    return data;
  },

  async createAction(taskId: string, payload: MethodActionCreate): Promise<MethodHumanAction> {
    const { data } = await api.post<MethodHumanAction>(`/api/v1/method-os/tasks/${taskId}/actions`, payload);
    return data;
  },

  async createOutcome(payload: MethodOutcomeCreate): Promise<MethodOutcome> {
    const { data } = await api.post<MethodOutcome>("/api/v1/method-os/outcomes", payload);
    return data;
  },

  async getDashboard(): Promise<MethodDashboard> {
    const { data } = await api.get<MethodDashboard>("/api/v1/method-os/dashboard/client");
    return data;
  },

  async generateWeeklyReport(payload: MethodWeeklyReportRequest = {}): Promise<MethodWeeklyReport> {
    const { data } = await api.post<MethodWeeklyReport>("/api/v1/method-os/reports/weekly", payload);
    return data;
  },
};

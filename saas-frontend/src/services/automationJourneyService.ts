import { api } from "./api";
import type {
  AutomationJourney,
  AutomationJourneyActivation,
  AutomationJourneyPreview,
  AutomationJourneyTemplate,
} from "../types";

export const automationJourneyService = {
  async listTemplates(): Promise<AutomationJourneyTemplate[]> {
    const { data } = await api.get<AutomationJourneyTemplate[]>("/api/v1/automation-journeys/templates");
    return data;
  },

  async listJourneys(): Promise<AutomationJourney[]> {
    const { data } = await api.get<AutomationJourney[]>("/api/v1/automation-journeys");
    return data;
  },

  async createFromTemplate(templateId: string): Promise<AutomationJourney> {
    const { data } = await api.post<AutomationJourney>("/api/v1/automation-journeys", { template_id: templateId });
    return data;
  },

  async previewTemplate(templateId: string): Promise<AutomationJourneyPreview> {
    const { data } = await api.post<AutomationJourneyPreview>("/api/v1/automation-journeys/preview", {
      template_id: templateId,
    });
    return data;
  },

  async previewJourney(journeyId: string): Promise<AutomationJourneyPreview> {
    const { data } = await api.post<AutomationJourneyPreview>(`/api/v1/automation-journeys/${journeyId}/preview`);
    return data;
  },

  async activateJourney(journeyId: string): Promise<AutomationJourneyActivation> {
    const { data } = await api.post<AutomationJourneyActivation>(`/api/v1/automation-journeys/${journeyId}/activate`);
    return data;
  },

  async pauseJourney(journeyId: string): Promise<AutomationJourney> {
    const { data } = await api.post<AutomationJourney>(`/api/v1/automation-journeys/${journeyId}/pause`);
    return data;
  },
};

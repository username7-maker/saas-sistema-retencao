import { api } from "./api";

export interface MessageTemplate {
  key: string;
  domain: string;
  channel: string;
  objective: string;
  content: string;
  default_content: string;
  allowed_variables: string[];
  required_variables: string[];
  version: string;
  active: boolean;
  origin: "template_default" | "template_gym_override";
}

export interface MessageComposition {
  request_id: string;
  base_message: string;
  improved_message: string | null;
  model: string | null;
  prompt_version: string | null;
  origin: "template_default" | "ai_improved";
  warnings: string[];
  status: "previewed" | "applied" | "discarded";
  created_at: string;
}

export const messageComposerService = {
  async listTemplates(): Promise<MessageTemplate[]> {
    const { data } = await api.get<MessageTemplate[]>("/api/v1/message-templates");
    return data;
  },

  async updateTemplate(templateKey: string, content: string): Promise<MessageTemplate> {
    const { data } = await api.put<MessageTemplate>(`/api/v1/message-templates/${templateKey}`, { content });
    return data;
  },

  async restoreTemplate(templateKey: string): Promise<MessageTemplate> {
    const { data } = await api.delete<MessageTemplate>(`/api/v1/message-templates/${templateKey}/override`);
    return data;
  },

  async improve(payload: {
    source_type: string;
    source_id: string | null;
    template_key: string;
    objective: string;
    idempotency_key: string;
  }): Promise<MessageComposition> {
    const { data } = await api.post<MessageComposition>("/api/v1/message-composer/improve", payload);
    return data;
  },

  async apply(requestId: string): Promise<MessageComposition> {
    const { data } = await api.post<MessageComposition>(`/api/v1/message-composer/${requestId}/apply`);
    return data;
  },

  async discard(requestId: string): Promise<MessageComposition> {
    const { data } = await api.post<MessageComposition>(`/api/v1/message-composer/${requestId}/discard`);
    return data;
  },
};

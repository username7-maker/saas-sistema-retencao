import { api } from "./api";

export interface AutomationRule {
  id: string;
  name: string;
  description: string | null;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  action_type: string;
  action_config: Record<string, unknown>;
  is_active: boolean;
  executions_count: number;
  last_executed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRuleCreate {
  name: string;
  description?: string;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  action_type: string;
  action_config: Record<string, unknown>;
  is_active?: boolean;
}

export interface AutomationRuleUpdate {
  name?: string;
  description?: string;
  trigger_config?: Record<string, unknown>;
  action_config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface MessageLog {
  id: string;
  member_id: string | null;
  automation_rule_id: string | null;
  channel: string;
  recipient: string;
  template_name: string | null;
  content: string;
  status: string;
  error_detail: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
}

export const automationService = {
  async listRules(activeOnly = false): Promise<AutomationRule[]> {
    const { data } = await api.get<AutomationRule[]>("/api/v1/automations/rules", {
      params: { active_only: activeOnly },
    });
    return data;
  },

  async getRule(ruleId: string): Promise<AutomationRule> {
    const { data } = await api.get<AutomationRule>(`/api/v1/automations/rules/${ruleId}`);
    return data;
  },

  async createRule(payload: AutomationRuleCreate): Promise<AutomationRule> {
    const { data } = await api.post<AutomationRule>("/api/v1/automations/rules", payload);
    return data;
  },

  async updateRule(ruleId: string, payload: AutomationRuleUpdate): Promise<AutomationRule> {
    const { data } = await api.patch<AutomationRule>(`/api/v1/automations/rules/${ruleId}`, payload);
    return data;
  },

  async deleteRule(ruleId: string): Promise<void> {
    await api.delete(`/api/v1/automations/rules/${ruleId}`);
  },

  async executeAll(): Promise<Record<string, unknown>[]> {
    const { data } = await api.post<Record<string, unknown>[]>("/api/v1/automations/execute");
    return data;
  },

  async seedDefaults(): Promise<AutomationRule[]> {
    const { data } = await api.post<AutomationRule[]>("/api/v1/automations/seed-defaults");
    return data;
  },

  async sendWhatsApp(payload: {
    phone: string;
    message: string;
    member_id?: string;
    template_name?: string;
  }): Promise<MessageLog> {
    const { data } = await api.post<MessageLog>("/api/v1/automations/whatsapp/send", payload);
    return data;
  },
};

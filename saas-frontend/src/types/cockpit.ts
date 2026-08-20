// Espelho literal dos contratos de GET /api/v1/cockpit/daily e /weekly-funnel
// (specs/slots/M1/cockpit-api/CONTRACT.md e specs/slots/M1/funnel-api/CONTRACT.md).

export interface CockpitLeadFollowup {
  lead_id: string;
  full_name: string;
  phone: string | null;
  stage: string;
  days_since_contact: number | null;
  reason: string;
  href: string;
}

export interface CockpitMemberAttention {
  member_id: string;
  full_name: string;
  risk_level: "red" | "yellow";
  retention_stage: string | null;
  days_without_checkin: number | null;
  reason: string;
  href: string;
}

export interface CockpitActionToday {
  task_id: string;
  title: string;
  priority: string;
  due_date: string | null;
  overdue: boolean;
  target_name: string | null;
  href: string;
}

export interface CockpitCounts {
  leads_followup: number;
  members_attention: number;
  actions_today: number;
}

export interface DailyCockpitResponse {
  generated_at: string;
  leads_followup: CockpitLeadFollowup[];
  members_attention: CockpitMemberAttention[];
  actions_today: CockpitActionToday[];
  triage_pending_count: number;
  counts: CockpitCounts;
}

export interface FunnelStage {
  key: string;
  label: string;
  value: number;
  previous_value: number;
}

export interface ConversionBreakdown {
  leads_won: number;
  members_joined: number;
  risk_recovered: number;
}

export interface WeeklyFunnelResponse {
  week_start: string;
  week_end: string;
  week_offset: number;
  contacts: FunnelStage;
  responses: FunnelStage;
  conversions: FunnelStage;
  conversion_breakdown: ConversionBreakdown;
}

export type Role = "owner" | "manager" | "salesperson" | "receptionist";

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type RiskLevel = "green" | "yellow" | "red";

export interface Member {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  status: "active" | "paused" | "cancelled";
  plan_name: string;
  monthly_fee: number;
  join_date: string;
  preferred_shift: string | null;
  nps_last_score: number;
  loyalty_months: number;
  risk_score: number;
  risk_level: RiskLevel;
  last_checkin_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  source: string;
  stage: "new" | "contact" | "visit" | "trial" | "proposal" | "won" | "lost";
  estimated_value: number;
  acquisition_cost: number;
  owner_id: string | null;
  last_contact_at: string | null;
  converted_member_id: string | null;
  notes: unknown[];
  lost_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  member_id: string | null;
  lead_id: string | null;
  assigned_to_user_id: string | null;
  priority: "low" | "medium" | "high" | "urgent";
  status: "todo" | "doing" | "done" | "cancelled";
  kanban_column: string;
  due_date: string | null;
  completed_at: string | null;
  suggested_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface RevenuePoint {
  month: string;
  value: number;
}

export interface ChurnPoint {
  month: string;
  churn_rate: number;
}

export interface LTVPoint {
  month: string;
  ltv: number;
}

export interface GrowthPoint {
  month: string;
  growth_mom: number;
}

export interface ExecutiveDashboard {
  total_members: number;
  active_members: number;
  mrr: number;
  churn_rate: number;
  nps_avg: number;
  risk_distribution: {
    green: number;
    yellow: number;
    red: number;
  };
}

export interface HeatmapPoint {
  weekday: number;
  hour_bucket: number;
  total_checkins: number;
}

export interface ConversionBySource {
  source: string;
  total: number;
  won: number;
  conversion_rate: number;
}

export interface ProjectionPoint {
  horizon_months: number;
  projected_revenue: number;
}

export interface NPSEvolutionPoint {
  month: string;
  average_score: number;
  responses: number;
}

export interface InAppNotification {
  id: string;
  member_id: string | null;
  user_id: string | null;
  title: string;
  message: string;
  category: string;
  read_at: string | null;
  created_at: string;
  extra_data: Record<string, unknown>;
}

export interface RiskAlert {
  id: string;
  member_id: string;
  score: number;
  level: RiskLevel;
  reasons: Record<string, unknown>;
  action_history: Array<Record<string, unknown>>;
  automation_stage: string | null;
  resolved: boolean;
  created_at: string;
}

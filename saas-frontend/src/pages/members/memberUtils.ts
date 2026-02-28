import type { Member, RiskLevel } from "../../types";
import type { MemberFilters } from "../../services/memberService";

export const PAGE_SIZE = 20;

export const RISK_LABELS: Record<RiskLevel, string> = {
  green: "Verde",
  yellow: "Amarelo",
  red: "Vermelho",
};

export const RISK_VARIANTS: Record<RiskLevel, "success" | "warning" | "danger"> = {
  green: "success",
  yellow: "warning",
  red: "danger",
};

export const STATUS_LABELS: Record<Member["status"], string> = {
  active: "Ativo",
  paused: "Pausado",
  cancelled: "Cancelado",
};

export const STATUS_VARIANTS: Record<Member["status"], "success" | "warning" | "danger"> = {
  active: "success",
  paused: "warning",
  cancelled: "danger",
};

export type MemberQueryFilters = Omit<MemberFilters, "page" | "page_size">;

export function todayIsoDate(): string {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

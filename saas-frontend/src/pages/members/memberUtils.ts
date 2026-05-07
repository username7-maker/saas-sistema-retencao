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

export const LIFECYCLE_LABELS: Record<string, string> = {
  active: "Rotina",
  onboarding: "Onboarding",
  attention: "Atencao",
  recovery: "Recuperacao",
  reactivation: "Reativacao",
  manager_escalation: "Gerente",
  cold_base: "Base fria",
  paused: "Pausado",
  cancelled: "Cancelado",
};

export const LIFECYCLE_VARIANTS: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  active: "success",
  onboarding: "info",
  attention: "warning",
  recovery: "danger",
  reactivation: "warning",
  manager_escalation: "danger",
  cold_base: "neutral",
  paused: "warning",
  cancelled: "neutral",
};

export const OWNER_ROLE_LABELS: Record<string, string> = {
  receptionist: "Recepcao",
  trainer: "Professor",
  manager: "Gerente",
  owner: "Owner",
  salesperson: "Comercial",
  system: "Sistema",
};

export function getLifecycleLabel(member: Member): string {
  if (member.lifecycle_label) return member.lifecycle_label;
  const stage = member.lifecycle_stage ?? "active";
  return LIFECYCLE_LABELS[stage] ?? stage;
}

export function getLifecycleVariant(member: Member): "neutral" | "success" | "warning" | "danger" | "info" {
  const stage = member.lifecycle_stage ?? "active";
  return LIFECYCLE_VARIANTS[stage] ?? "neutral";
}

export function getOwnerRoleLabel(role?: string | null): string | null {
  if (!role) return null;
  return OWNER_ROLE_LABELS[role] ?? role;
}

export type MemberQueryFilters = Omit<MemberFilters, "page" | "page_size">;

export function getMemberExternalId(member: Member): string | null {
  const value = member.extra_data?.external_id;
  return typeof value === "string" && value.trim() ? value : null;
}

export function isProvisionalMember(member: Member): boolean {
  const value = member.extra_data?.provisional_member;
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return value === "true";
  return false;
}

export function todayIsoDate(): string {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

const PT_MONTHS: Record<string, number> = {
  janeiro: 0,
  fevereiro: 1,
  marco: 2,
  abril: 3,
  maio: 4,
  junho: 5,
  julho: 6,
  agosto: 7,
  setembro: 8,
  outubro: 9,
  novembro: 10,
  dezembro: 11,
};

function normalizeMonthToken(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function parseBirthdayLabel(label: string, year: number): Date | null {
  const match = label.match(/(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)/i);
  if (!match) return null;
  const day = Number(match[1]);
  const month = PT_MONTHS[normalizeMonthToken(match[2])];
  if (!Number.isInteger(day) || month === undefined) return null;
  return new Date(year, month, day, 12, 0, 0, 0);
}

function resolveMemberBirthday(member: Member, reference = new Date()): Date | null {
  if (member.birthdate) {
    const parsed = new Date(`${member.birthdate}T12:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const label = member.extra_data?.birthday_label;
  return typeof label === "string" ? parseBirthdayLabel(label, reference.getFullYear()) : null;
}

export function getUpcomingBirthdayLabel(member: Member, reference = new Date()): string | null {
  const birthday = resolveMemberBirthday(member, reference);
  if (!birthday) return null;

  const today = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate(), 12, 0, 0, 0);
  let nextBirthday = new Date(today.getFullYear(), birthday.getMonth(), birthday.getDate(), 12, 0, 0, 0);
  if (nextBirthday < today) {
    nextBirthday = new Date(today.getFullYear() + 1, birthday.getMonth(), birthday.getDate(), 12, 0, 0, 0);
  }

  const diffDays = Math.round((nextBirthday.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0 || diffDays > 7) return null;
  if (diffDays === 0) return "Aniversário hoje";
  if (diffDays === 1) return "Aniversário amanhã";
  return `Aniversário em ${diffDays} dias`;
}

import type { Role } from "../types";

export const ROUTE_ACCESS = {
  members: ["owner", "manager", "receptionist", "salesperson"],
  dashboardExecutive: ["owner", "manager"],
  dashboardOperational: ["owner", "manager", "receptionist"],
  dashboardCommercial: ["owner", "manager", "salesperson"],
  dashboardFinancial: ["owner", "manager"],
  dashboardRetention: ["owner", "manager", "receptionist"],
  crm: ["owner", "manager", "salesperson", "receptionist"],
  tasks: ["owner", "manager", "receptionist", "salesperson"],
  goals: ["owner", "manager"],
  reports: ["owner", "manager"],
  assessments: ["owner", "manager", "receptionist", "trainer"],
  assessmentContext: ["owner", "manager", "receptionist", "salesperson", "trainer"],
  assessmentRegistration: ["owner", "manager", "trainer"],
  notifications: ["owner", "manager", "receptionist", "salesperson"],
  automations: ["owner", "manager"],
  imports: ["owner", "manager"],
  userAdmin: ["owner", "manager"],
  nps: ["owner", "manager", "receptionist", "salesperson"],
  audit: ["owner", "manager"],
  sales: ["owner", "manager", "salesperson"],
} as const;

export type RouteAccessKey = keyof typeof ROUTE_ACCESS;
export type AssessmentWorkspaceTab =
  | "overview"
  | "registro"
  | "evolucao"
  | "plano"
  | "contexto"
  | "acoes"
  | "bioimpedancia";

const ROUTE_MATCHERS: Array<{ route: RouteAccessKey; matches: (path: string) => boolean }> = [
  { route: "members", matches: (path) => path === "/members" },
  { route: "dashboardExecutive", matches: (path) => path.startsWith("/dashboard/executive") },
  { route: "dashboardOperational", matches: (path) => path.startsWith("/dashboard/operational") },
  { route: "dashboardCommercial", matches: (path) => path.startsWith("/dashboard/commercial") },
  { route: "dashboardFinancial", matches: (path) => path.startsWith("/dashboard/financial") },
  { route: "dashboardRetention", matches: (path) => path.startsWith("/dashboard/retention") },
  { route: "crm", matches: (path) => path === "/crm" },
  { route: "tasks", matches: (path) => path.startsWith("/tasks") },
  { route: "goals", matches: (path) => path.startsWith("/goals") },
  { route: "reports", matches: (path) => path.startsWith("/reports") },
  { route: "assessmentContext", matches: (path) => path.startsWith("/assessments/members/") },
  { route: "assessmentRegistration", matches: (path) => path.startsWith("/assessments/new/") },
  { route: "assessments", matches: (path) => path.startsWith("/assessments") },
  { route: "notifications", matches: (path) => path.startsWith("/notifications") },
  { route: "automations", matches: (path) => path.startsWith("/automations") },
  { route: "imports", matches: (path) => path.startsWith("/imports") },
  { route: "userAdmin", matches: (path) => path.startsWith("/settings/users") },
  { route: "nps", matches: (path) => path.startsWith("/nps") },
  { route: "audit", matches: (path) => path.startsWith("/audit") },
  { route: "sales", matches: (path) => path.startsWith("/vendas/") },
];

function hasRole(role: Role | null | undefined, allowedRoles: readonly Role[]): boolean {
  return Boolean(role && allowedRoles.includes(role));
}

export const USER_ADMIN_ROLES: Role[] = [...ROUTE_ACCESS.userAdmin];
export const NON_TRAINER_ROLES: Role[] = ["owner", "manager", "receptionist", "salesperson"];

export function canManageUsers(role: Role | null | undefined): boolean {
  return hasRole(role, ROUTE_ACCESS.userAdmin);
}

export function canToggleUsers(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canChangeUserRole(role: Role | null | undefined): boolean {
  return role === "owner";
}

export function canCreateUsers(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function getAssignableUserRoles(role: Role | null | undefined): Role[] {
  if (role === "owner") {
    return ["manager", "receptionist", "salesperson", "trainer"];
  }
  if (role === "manager") {
    return ["receptionist", "salesperson", "trainer"];
  }
  return [];
}

export function canToggleTargetUser(actorRole: Role | null | undefined, targetRole: Role, isSelf: boolean): boolean {
  if (isSelf || !canToggleUsers(actorRole)) return false;
  if (actorRole === "owner") return targetRole !== "owner";
  if (actorRole === "manager") return targetRole !== "owner";
  return false;
}

export function canEditTargetUserProfile(actorRole: Role | null | undefined, targetRole: Role, isSelf: boolean): boolean {
  if (isSelf) return false;
  if (actorRole === "owner") return true;
  if (actorRole === "manager") return targetRole !== "owner";
  return false;
}

export function canEditTargetUserRole(actorRole: Role | null | undefined, targetRole: Role, isSelf: boolean): boolean {
  if (isSelf) return false;
  return actorRole === "owner" && targetRole !== "owner";
}

export function canManageMemberDirectory(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "receptionist";
}

export function canDeleteMember(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canAccessRoute(role: Role | null | undefined, route: RouteAccessKey): boolean {
  return hasRole(role, ROUTE_ACCESS[route]);
}

export function getDefaultRouteForRole(role: Role | null | undefined): string {
  if (role === "trainer") return "/assessments";
  if (role === "receptionist") return "/dashboard/operational";
  if (role === "salesperson") return "/crm";
  return "/dashboard/executive";
}

export function canRoleAccessPath(role: Role | null | undefined, path: string | null | undefined): boolean {
  if (!role || !path) return false;
  if (path === "/settings" || path.startsWith("/settings?")) {
    return true;
  }

  const routeMatch = ROUTE_MATCHERS.find((entry) => entry.matches(path));
  if (!routeMatch) return false;
  return canAccessRoute(role, routeMatch.route);
}

export function resolvePostLoginRoute(role: Role | null | undefined, from: string | null | undefined): string {
  if (from && canRoleAccessPath(role, from)) {
    return from;
  }
  return getDefaultRouteForRole(role);
}

export function canViewAiInsight(role: Role | null | undefined, dashboard: "executive" | "retention" | "operational" | "commercial" | "financial"): boolean {
  if (dashboard === "operational") return role === "owner" || role === "manager";
  if (dashboard === "retention") return role === "owner" || role === "manager";
  if (dashboard === "commercial") return role === "owner" || role === "manager";
  return role === "owner" || role === "manager";
}

export function canExportDashboardReport(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canDispatchMonthlyReports(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canResolveRetentionAlert(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canDispatchNps(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canExportLgpd(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canAnonymizeLgpd(role: Role | null | undefined): boolean {
  return role === "owner";
}

export function canAccessCrm(role: Role | null | undefined): boolean {
  return hasRole(role, ROUTE_ACCESS.crm);
}

export function canMutateCrm(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "salesperson";
}

export function canDeleteLead(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canSeedAutomationRules(role: Role | null | undefined): boolean {
  return role === "owner";
}

export function canDeleteAutomationRules(role: Role | null | undefined): boolean {
  return role === "owner";
}

export function canCreateAssessment(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "trainer";
}

export function canEditAssessmentPlan(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "trainer";
}

export function canEditAssessmentConstraints(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "trainer";
}

export function canAddAssessmentInternalNote(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function canViewAssessmentTasks(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "receptionist" || role === "trainer";
}

export function canCreateAssessmentTasks(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "receptionist";
}

export function canUpdateAssessmentTasks(role: Role | null | undefined): boolean {
  return canViewAssessmentTasks(role);
}

export function canViewAssessmentTimeline(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "receptionist";
}

export function canManageBodyComposition(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "receptionist" || role === "trainer";
}

export function canManageActuarSync(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager" || role === "receptionist";
}

export function getVisibleAssessmentWorkspaceTabs(role: Role | null | undefined): AssessmentWorkspaceTab[] {
  if (role === "trainer") {
    return ["overview", "registro", "evolucao", "plano", "contexto", "acoes", "bioimpedancia"];
  }
  if (role === "salesperson") {
    return ["overview", "evolucao"];
  }
  if (role === "receptionist") {
    return ["overview", "evolucao", "acoes", "bioimpedancia"];
  }
  return ["overview", "registro", "evolucao", "plano", "contexto", "acoes", "bioimpedancia"];
}

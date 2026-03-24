import type { Role } from "../types";

export const NON_TRAINER_ROLES: Role[] = ["owner", "manager", "receptionist", "salesperson"];
export const USER_ADMIN_ROLES: Role[] = ["owner", "manager"];

export function canManageUsers(role: Role | null | undefined): boolean {
  return role === "owner" || role === "manager";
}

export function getDefaultRouteForRole(role: Role | null | undefined): string {
  if (role === "trainer") return "/assessments";
  if (role === "receptionist") return "/dashboard/operational";
  if (role === "salesperson") return "/crm";
  return "/dashboard/executive";
}

export function canRoleAccessPath(role: Role | null | undefined, path: string | null | undefined): boolean {
  if (!role || !path) return false;
  if (role !== "trainer") return true;
  return path === "/settings" || path.startsWith("/assessments");
}

export function resolvePostLoginRoute(role: Role | null | undefined, from: string | null | undefined): string {
  if (from && canRoleAccessPath(role, from)) {
    return from;
  }
  return getDefaultRouteForRole(role);
}

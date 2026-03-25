import { describe, expect, it } from "vitest";

import {
  canDeleteAutomationRules,
  canRoleAccessPath,
  canSeedAutomationRules,
  getDefaultRouteForRole,
  resolvePostLoginRoute,
} from "../utils/roleAccess";

describe("roleAccess", () => {
  it("routes each role to its default home", () => {
    expect(getDefaultRouteForRole("owner")).toBe("/dashboard/executive");
    expect(getDefaultRouteForRole("manager")).toBe("/dashboard/executive");
    expect(getDefaultRouteForRole("receptionist")).toBe("/dashboard/operational");
    expect(getDefaultRouteForRole("salesperson")).toBe("/crm");
    expect(getDefaultRouteForRole("trainer")).toBe("/assessments");
  });

  it("keeps the requested path only when the role can access it", () => {
    expect(resolvePostLoginRoute("trainer", "/assessments/members/member-1")).toBe("/assessments/members/member-1");
    expect(resolvePostLoginRoute("trainer", "/settings/users")).toBe("/assessments");
    expect(resolvePostLoginRoute("salesperson", "/crm")).toBe("/crm");
    expect(resolvePostLoginRoute("salesperson", "/assessments/members/member-1")).toBe("/assessments/members/member-1");
  });

  it("matches the contained navigation surface for receptionist and salesperson", () => {
    expect(canRoleAccessPath("receptionist", "/crm")).toBe(true);
    expect(canRoleAccessPath("receptionist", "/imports")).toBe(false);
    expect(canRoleAccessPath("salesperson", "/dashboard/operational")).toBe(false);
    expect(canRoleAccessPath("salesperson", "/crm")).toBe(true);
    expect(canRoleAccessPath("salesperson", "/assessments/members/member-1")).toBe(true);
    expect(canRoleAccessPath("salesperson", "/assessments/new/member-1")).toBe(false);
    expect(canRoleAccessPath("trainer", "/assessments/new/member-1")).toBe(true);
  });

  it("keeps seed and delete automation controls owner-only", () => {
    expect(canSeedAutomationRules("owner")).toBe(true);
    expect(canSeedAutomationRules("manager")).toBe(false);
    expect(canDeleteAutomationRules("owner")).toBe(true);
    expect(canDeleteAutomationRules("manager")).toBe(false);
  });
});

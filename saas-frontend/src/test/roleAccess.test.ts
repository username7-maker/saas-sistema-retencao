import { describe, expect, it } from "vitest";

import { getDefaultRouteForRole, resolvePostLoginRoute } from "../utils/roleAccess";

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
  });
});

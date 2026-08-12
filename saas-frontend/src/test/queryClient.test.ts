import { describe, expect, it } from "vitest";

import { createAppQueryClient } from "../services/queryClient";


describe("application query recovery", () => {
  it("refetches stale data after focus/reconnect and tolerates transient failures", () => {
    const options = createAppQueryClient().getDefaultOptions().queries;

    expect(options?.refetchOnWindowFocus).toBe(true);
    expect(options?.refetchOnReconnect).toBe(true);
    expect(options?.retry).toBe(2);
  });
});

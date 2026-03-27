import { describe, expect, it } from "vitest";

import { getChartSeriesState } from "../components/charts/chartState";

describe("getChartSeriesState", () => {
  it("marks empty input as no points", () => {
    expect(getChartSeriesState([], ["value"])).toEqual({
      hasPoints: false,
      finiteCount: 0,
      hasMeaningfulValues: false,
      isAllZero: false,
      isFlat: false,
    });
  });

  it("detects all-zero series as lacking meaningful values", () => {
    const state = getChartSeriesState(
      [
        { month: "2026-01", value: 0 },
        { month: "2026-02", value: 0 },
        { month: "2026-03", value: 0 },
      ],
      ["value"],
    );

    expect(state.hasPoints).toBe(true);
    expect(state.finiteCount).toBe(3);
    expect(state.hasMeaningfulValues).toBe(false);
    expect(state.isAllZero).toBe(true);
    expect(state.isFlat).toBe(true);
  });

  it("detects mixed series as meaningful", () => {
    const state = getChartSeriesState(
      [
        { month: "2026-01", churn_rate: 0, nps_avg: null },
        { month: "2026-02", churn_rate: 2.5, nps_avg: 6.8 },
      ],
      ["churn_rate", "nps_avg"],
    );

    expect(state.hasMeaningfulValues).toBe(true);
    expect(state.isAllZero).toBe(false);
    expect(state.isFlat).toBe(false);
  });
});

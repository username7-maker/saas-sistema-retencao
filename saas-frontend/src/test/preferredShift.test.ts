import { describe, expect, it } from "vitest";
import { getPreferredShiftKey, getPreferredShiftLabel, matchesPreferredShift } from "../utils/preferredShift";

describe("preferredShift utils", () => {
  it("normalizes supported shift aliases", () => {
    expect(getPreferredShiftKey("madrugada")).toBe("overnight");
    expect(getPreferredShiftKey("manha")).toBe("morning");
    expect(getPreferredShiftKey("tarde")).toBe("afternoon");
    expect(getPreferredShiftKey("noite")).toBe("evening");
  });

  it("hides noisy legacy values", () => {
    expect(getPreferredShiftKey("LIVRE, LIVRE")).toBeNull();
    expect(getPreferredShiftLabel("LIVRE, LIVRE")).toBeNull();
    expect(matchesPreferredShift("LIVRE, LIVRE", "morning")).toBe(false);
  });

  it("matches overnight aliases", () => {
    expect(getPreferredShiftLabel("plantao_madrugada")).toBe("Madrugada");
    expect(matchesPreferredShift("madrugada", "overnight")).toBe(true);
  });
});

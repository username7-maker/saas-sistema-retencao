import { beforeEach, describe, expect, it } from "vitest";

import { tokenStorage } from "../services/storage";

describe("tokenStorage", () => {
  beforeEach(() => {
    tokenStorage.clear();
    window.localStorage.clear();
  });

  it("stores the access token in session storage for F5 recovery", () => {
    tokenStorage.setAccessToken("access-token");

    expect(tokenStorage.getAccessToken()).toBe("access-token");
    expect(window.sessionStorage.getItem("ai_gym_access_token")).toBe("access-token");
    expect(window.localStorage.getItem("ai_gym_access_token")).toBeNull();
    expect(window.localStorage.getItem("ai_gym_refresh_token")).toBeNull();
  });

  it("migrates a legacy access token out of localStorage into sessionStorage", () => {
    window.localStorage.setItem("ai_gym_access_token", "legacy-access");
    window.localStorage.setItem("ai_gym_refresh_token", "legacy-refresh");

    expect(tokenStorage.getAccessToken()).toBe("legacy-access");
    expect(window.sessionStorage.getItem("ai_gym_access_token")).toBe("legacy-access");
    expect(window.localStorage.getItem("ai_gym_access_token")).toBeNull();
    expect(window.localStorage.getItem("ai_gym_refresh_token")).toBeNull();
  });

  it("clears session and legacy token stores", () => {
    tokenStorage.setAccessToken("access-token");
    window.localStorage.setItem("ai_gym_access_token", "legacy-access");
    window.localStorage.setItem("ai_gym_refresh_token", "legacy-refresh");

    tokenStorage.clear();

    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(window.sessionStorage.getItem("ai_gym_access_token")).toBeNull();
    expect(window.localStorage.getItem("ai_gym_access_token")).toBeNull();
    expect(window.localStorage.getItem("ai_gym_refresh_token")).toBeNull();
  });
});

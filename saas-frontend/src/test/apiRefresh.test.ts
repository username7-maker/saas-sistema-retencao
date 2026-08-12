import { beforeEach, describe, expect, it, vi } from "vitest";

const axiosPostMock = vi.hoisted(() => vi.fn());
const isAxiosErrorMock = vi.hoisted(() => vi.fn());
const requestInterceptorUseMock = vi.hoisted(() => vi.fn());
const responseInterceptorUseMock = vi.hoisted(() => vi.fn());

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: requestInterceptorUseMock },
        response: { use: responseInterceptorUseMock },
      },
    })),
    post: axiosPostMock,
    isAxiosError: isAxiosErrorMock,
  },
}));

import { ensureFreshAccessToken, isAccessTokenExpiringSoon, requestAccessTokenRefresh } from "../services/api";
import { tokenStorage } from "../services/storage";

function tokenWithExp(exp: number): string {
  const payload = window.btoa(JSON.stringify({ exp })).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `header.${payload}.signature`;
}

describe("requestAccessTokenRefresh", () => {
  beforeEach(() => {
    axiosPostMock.mockReset();
    isAxiosErrorMock.mockReset();
    tokenStorage.clear();
    window.localStorage.clear();
  });

  it("stores the new access token when refresh succeeds", async () => {
    axiosPostMock.mockResolvedValueOnce({
      data: {
        access_token: "new-access-token",
        refresh_token: null,
        token_type: "bearer",
        expires_in: 900,
      },
    });

    await expect(requestAccessTokenRefresh()).resolves.toBe("new-access-token");

    expect(tokenStorage.getAccessToken()).toBe("new-access-token");
  });

  it("keeps the access token when refresh fails transiently", async () => {
    tokenStorage.setAccessToken("current-access-token");
    const error = Object.assign(new Error("refresh failed"), { response: { status: 500 } });
    axiosPostMock.mockRejectedValueOnce(error);
    isAxiosErrorMock.mockReturnValueOnce(true);

    await expect(requestAccessTokenRefresh()).rejects.toThrow("refresh failed");

    expect(tokenStorage.getAccessToken()).toBe("current-access-token");
  });

  it("clears the access token when refresh is rejected by auth", async () => {
    tokenStorage.setAccessToken("current-access-token");
    const error = Object.assign(new Error("refresh unauthorized"), { response: { status: 401 } });
    axiosPostMock.mockRejectedValueOnce(error);
    isAxiosErrorMock.mockReturnValueOnce(true);

    await expect(requestAccessTokenRefresh()).rejects.toThrow("refresh unauthorized");

    expect(tokenStorage.getAccessToken()).toBeNull();
  });

  it("keeps the access token when refresh fails with clearOnFailure disabled", async () => {
    tokenStorage.setAccessToken("current-access-token");
    axiosPostMock.mockRejectedValueOnce(new Error("refresh failed"));

    await expect(requestAccessTokenRefresh({ clearOnFailure: false })).rejects.toThrow("refresh failed");

    expect(tokenStorage.getAccessToken()).toBe("current-access-token");
  });
});

describe("ensureFreshAccessToken", () => {
  beforeEach(() => {
    axiosPostMock.mockReset();
    isAxiosErrorMock.mockReset();
    tokenStorage.clear();
    window.localStorage.clear();
  });

  it("keeps a comfortably valid access token without rotating the refresh cookie", async () => {
    const expiresInTenMinutes = Math.floor((Date.now() + 10 * 60_000) / 1000);
    const token = tokenWithExp(expiresInTenMinutes);
    tokenStorage.setAccessToken(token);

    await expect(ensureFreshAccessToken()).resolves.toBe(token);

    expect(axiosPostMock).not.toHaveBeenCalled();
  });

  it("refreshes when the access token is inside the keepalive window", async () => {
    const expiresInFiveMinutes = Math.floor((Date.now() + 5 * 60_000) / 1000);
    tokenStorage.setAccessToken(tokenWithExp(expiresInFiveMinutes));
    axiosPostMock.mockResolvedValueOnce({
      data: {
        access_token: "fresh-access-token",
        refresh_token: null,
        token_type: "bearer",
        expires_in: 900,
      },
    });

    await expect(ensureFreshAccessToken({ clearOnFailure: false })).resolves.toBe("fresh-access-token");

    expect(tokenStorage.getAccessToken()).toBe("fresh-access-token");
  });
});

describe("isAccessTokenExpiringSoon", () => {
  it("requests proactive refresh when the access token is close to expiration", () => {
    const nowMs = Date.UTC(2026, 0, 1, 12, 0, 0);
    const expiresInOneMinute = Math.floor((nowMs + 60_000) / 1000);

    expect(isAccessTokenExpiringSoon(tokenWithExp(expiresInOneMinute), nowMs)).toBe(true);
  });

  it("keeps fresh access tokens without an unnecessary refresh", () => {
    const nowMs = Date.UTC(2026, 0, 1, 12, 0, 0);
    const expiresInTenMinutes = Math.floor((nowMs + 10 * 60_000) / 1000);

    expect(isAccessTokenExpiringSoon(tokenWithExp(expiresInTenMinutes), nowMs)).toBe(false);
  });

  it("treats malformed tokens as refresh candidates", () => {
    expect(isAccessTokenExpiringSoon("not-a-jwt", Date.UTC(2026, 0, 1))).toBe(true);
  });
});

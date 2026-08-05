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

import { requestAccessTokenRefresh } from "../services/api";
import { tokenStorage } from "../services/storage";

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

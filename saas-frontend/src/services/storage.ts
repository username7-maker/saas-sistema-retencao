const ACCESS_TOKEN_KEY = "ai_gym_access_token";
const LEGACY_REFRESH_TOKEN_KEY = "ai_gym_refresh_token";

let inMemoryAccessToken: string | null = null;

function getLocalStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export const tokenStorage = {
  getAccessToken: (): string | null => {
    const localStorage = getLocalStorage();
    if (inMemoryAccessToken) {
      return inMemoryAccessToken;
    }

    const legacyToken = localStorage?.getItem(ACCESS_TOKEN_KEY) ?? null;
    if (legacyToken) {
      inMemoryAccessToken = legacyToken;
      localStorage?.removeItem(ACCESS_TOKEN_KEY);
    }
    localStorage?.removeItem(LEGACY_REFRESH_TOKEN_KEY);
    return legacyToken;
  },
  setAccessToken: (accessToken: string): void => {
    inMemoryAccessToken = accessToken;
    const localStorage = getLocalStorage();
    localStorage?.removeItem(ACCESS_TOKEN_KEY);
    localStorage?.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  },
  clear: (): void => {
    inMemoryAccessToken = null;
    const localStorage = getLocalStorage();
    localStorage?.removeItem(ACCESS_TOKEN_KEY);
    localStorage?.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  },
};

const ACCESS_TOKEN_KEY = "ai_gym_access_token";
const LEGACY_REFRESH_TOKEN_KEY = "ai_gym_refresh_token";

function getSessionStorage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function getLocalStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export const tokenStorage = {
  getAccessToken: (): string | null => {
    const sessionStorage = getSessionStorage();
    const localStorage = getLocalStorage();
    const sessionToken = sessionStorage?.getItem(ACCESS_TOKEN_KEY);
    if (sessionToken) {
      return sessionToken;
    }

    const legacyToken = localStorage?.getItem(ACCESS_TOKEN_KEY) ?? null;
    if (legacyToken) {
      sessionStorage?.setItem(ACCESS_TOKEN_KEY, legacyToken);
      localStorage?.removeItem(ACCESS_TOKEN_KEY);
    }
    localStorage?.removeItem(LEGACY_REFRESH_TOKEN_KEY);
    return legacyToken;
  },
  setAccessToken: (accessToken: string): void => {
    getSessionStorage()?.setItem(ACCESS_TOKEN_KEY, accessToken);
    const localStorage = getLocalStorage();
    localStorage?.removeItem(ACCESS_TOKEN_KEY);
    localStorage?.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  },
  clear: (): void => {
    getSessionStorage()?.removeItem(ACCESS_TOKEN_KEY);
    const localStorage = getLocalStorage();
    localStorage?.removeItem(ACCESS_TOKEN_KEY);
    localStorage?.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  },
};

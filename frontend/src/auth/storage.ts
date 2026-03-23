import type { AuthSession, AuthUser } from "@/types/auth.ts";

const ACCESS_TOKEN_KEY = "den.auth.accessToken";
const TOKEN_TYPE_KEY = "den.auth.tokenType";
const EXPIRES_AT_KEY = "den.auth.expiresAt";
const USER_KEY = "den.auth.user";

const normalizeTokenType = (tokenType: string): string => {
    return tokenType.toLowerCase() === "bearer" ? "Bearer" : tokenType;
};

export const saveAuthSession = (session: AuthSession): void => {
    localStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
    localStorage.setItem(TOKEN_TYPE_KEY, session.tokenType);
    localStorage.setItem(EXPIRES_AT_KEY, String(session.expiresAt));
    localStorage.setItem(USER_KEY, JSON.stringify(session.user));
};

export const clearAuthSession = (): void => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(TOKEN_TYPE_KEY);
    localStorage.removeItem(EXPIRES_AT_KEY);
    localStorage.removeItem(USER_KEY);
};

export const getStoredAuthSession = (): AuthSession | null => {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const tokenType = localStorage.getItem(TOKEN_TYPE_KEY);
    const expiresAtRaw = localStorage.getItem(EXPIRES_AT_KEY);
    const userRaw = localStorage.getItem(USER_KEY);

    if (!accessToken || !tokenType || !expiresAtRaw || !userRaw) {
        return null;
    }

    const expiresAt = Number(expiresAtRaw);

    if (!Number.isFinite(expiresAt) || Date.now() >= expiresAt) {
        clearAuthSession();
        return null;
    }

    try {
        const user = JSON.parse(userRaw) as AuthUser;
        const expiresIn = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));

        return {
            accessToken,
            tokenType,
            expiresAt,
            expiresIn,
            user,
        };
    } catch {
        clearAuthSession();
        return null;
    }
};

export const getAccessToken = (): string | null => {
    return getStoredAuthSession()?.accessToken ?? null;
};

export const getAuthorizationHeaderValue = (): string | null => {
    const session = getStoredAuthSession();

    if (!session) {
        return null;
    }

    return `${normalizeTokenType(session.tokenType)} ${session.accessToken}`;
};

export const isAuthenticated = (): boolean => {
    return getStoredAuthSession() !== null;
};
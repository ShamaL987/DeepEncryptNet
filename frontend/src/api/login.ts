import {API_BASE, apiPost} from "@/api/index.ts";
import type {
    AuthSession, GenerateApiTokenResponseDto,
    LoginFormValues,
    LoginResponseDto, RevokeApiTokenResponseDto,
} from "@/types/auth.ts";
import {
    mapLoginFormToRequest,
    mapLoginResponseToSession,
} from "@/mappers/auth.ts";
import {
    clearAuthSession,
    getStoredAuthSession,
    saveAuthSession,
} from "@/auth/storage.ts";


export const login = async (
    values: LoginFormValues,
): Promise<AuthSession> => {
    const response = await fetch(`${API_BASE}/user/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify(mapLoginFormToRequest(values)),
    });

    const responseData = await response.json().catch(() => null);

    if (!response.ok) {
        const errorMessage =
            typeof responseData?.detail === "string"
                ? responseData.detail
                : "Failed to login";

        throw new Error(errorMessage);
    }

    const session = mapLoginResponseToSession(responseData as LoginResponseDto);
    saveAuthSession(session);

    return session;
};

export const generateApiToken = async (): Promise<GenerateApiTokenResponseDto> => {
    const response = await apiPost("/user/auth/generate");

    const responseData = await response.json().catch(() => null);

    if (!response.ok) {
        const errorMessage =
            typeof responseData?.detail === "string"
                ? responseData.detail
                : "Failed to generate API token";

        throw new Error(errorMessage);
    }

    return responseData as GenerateApiTokenResponseDto;
};

export const revokeApiToken = async (): Promise<RevokeApiTokenResponseDto> => {
    const response = await apiPost("/user/auth/revoke");

    const responseData = await response.json().catch(() => null);

    if (!response.ok) {
        const errorMessage =
            typeof responseData?.detail === "string"
                ? responseData.detail
                : "Failed to revoke API token";

        throw new Error(errorMessage);
    }

    return responseData as RevokeApiTokenResponseDto;
};

export const logout = (): void => {
    clearAuthSession();
};

export const getAuthSession = (): AuthSession | null => {
    return getStoredAuthSession();
};
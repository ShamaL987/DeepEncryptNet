import type {
    AuthSession,
    LoginFormValues,
    LoginRequestDto,
    LoginResponseDto,
} from "@/types/auth.ts";

export const mapLoginFormToRequest = (
    values: LoginFormValues,
): LoginRequestDto => {
    return {
        identifier: values.identifier.trim(),
        password: values.password,
    };
};

export const mapLoginResponseToSession = (
    response: LoginResponseDto,
): AuthSession => {
    return {
        accessToken: response.access_token,
        tokenType: response.token_type,
        expiresIn: response.expires_in,
        expiresAt: Date.now() + response.expires_in * 1000,
        user: {
            id: response.user.id,
            username: response.user.username,
            email: response.user.email,
        },
    };
};
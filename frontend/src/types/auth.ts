export interface LoginFormValues {
    identifier: string;
    password: string;
}

export interface LoginRequestDto {
    identifier: string;
    password: string;
}

export interface AuthUserDto {
    id: number;
    username: string;
    email: string;
}

export interface LoginResponseDto {
    access_token: string;
    token_type: string;
    expires_in: number;
    user: AuthUserDto;
}

export interface AuthUser {
    id: number;
    username: string;
    email: string;
}

export interface AuthSession {
    accessToken: string;
    tokenType: string;
    expiresIn: number;
    expiresAt: number;
    user: AuthUser;
}


export interface GenerateApiTokenResponseDto {
    token: string;
    token_prefix: string;
    generated_at: string | null;
    replaced_existing: boolean;
}

export interface RevokeApiTokenResponseDto {
    revoked: boolean;
    revoked_at?: string | null;
    message?: string;
}
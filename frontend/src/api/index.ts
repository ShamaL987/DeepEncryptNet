import { getAuthorizationHeaderValue } from "@/auth/storage.ts";


export const APP_ENV = import.meta.env.VITE_APP_ENV || "local";
export const API_BASE =
  APP_ENV === "production"
    ? "/api"
    : "http://localhost:8000/api";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";


interface ApiRequestOptions extends Omit<RequestInit, "method" | "body" | "headers"> {
    method?: HttpMethod;
    body?: BodyInit | object | null;
    headers?: HeadersInit;
}

const isPlainObject = (value: unknown): value is Record<string, unknown> => {
    return typeof value === "object" && value !== null && !(value instanceof FormData) && !(value instanceof Blob);
};

export async function apiRequest(
    path: string,
    options: ApiRequestOptions = {},
): Promise<Response> {
    const {
        method = "GET",
        body,
        headers,
        ...rest
    } = options;

    const authorizationHeader = getAuthorizationHeaderValue();
    const requestHeaders = new Headers(headers);

    if (!requestHeaders.has("Accept")) {
        requestHeaders.set("Accept", "application/json");
    }

    if (authorizationHeader && !requestHeaders.has("Authorization")) {
        requestHeaders.set("Authorization", authorizationHeader);
    }

    let requestBody: BodyInit | undefined;

    if (body == null) {
        requestBody = undefined;
    } else if (body instanceof FormData || body instanceof Blob || typeof body === "string") {
        requestBody = body;
    } else if (isPlainObject(body)) {
        if (!requestHeaders.has("Content-Type")) {
            requestHeaders.set("Content-Type", "application/json");
        }
        requestBody = JSON.stringify(body);
    } else {
        requestBody = body as BodyInit;
    }

    return fetch(`${API_BASE}${path}`, {
        ...rest,
        method,
        headers: requestHeaders,
        body: requestBody,
    });
}

export async function apiGet(path: string, init: Omit<ApiRequestOptions, "method" | "body"> = {}) {
    return apiRequest(path, { ...init, method: "GET" });
}

export async function apiPost(
    path: string,
    body?: BodyInit | object | null,
    init: Omit<ApiRequestOptions, "method" | "body"> = {},
) {
    return apiRequest(path, { ...init, method: "POST", body });
}

export async function apiPut(
    path: string,
    body?: BodyInit | object | null,
    init: Omit<ApiRequestOptions, "method" | "body"> = {},
) {
    return apiRequest(path, { ...init, method: "PUT", body });
}

export async function apiPatch(
    path: string,
    body?: BodyInit | object | null,
    init: Omit<ApiRequestOptions, "method" | "body"> = {},
) {
    return apiRequest(path, { ...init, method: "PATCH", body });
}

export async function apiDelete(
    path: string,
    init: Omit<ApiRequestOptions, "method" | "body"> = {},
) {
    return apiRequest(path, { ...init, method: "DELETE" });
}
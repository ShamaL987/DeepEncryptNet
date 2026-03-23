import type { FlowDaemonOverviewResponse } from "@/types/daemon";
import { apiGet, apiPost, apiPut } from "@/api/index.ts";

export async function fetchOverview(): Promise<FlowDaemonOverviewResponse> {
    const response = await apiGet("/health/overview");

    if (!response.ok) {
        throw new Error("Failed to fetch daemon overview");
    }

    return response.json();
}

export async function startPipeline() {
    const response = await apiPost("/health/start");

    if (!response.ok) {
        throw new Error("Failed to start pipeline");
    }

    return response.json();
}

export async function stopPipeline() {
    const response = await apiPost("/health/stop");

    if (!response.ok) {
        throw new Error("Failed to stop pipeline");
    }

    return response.json();
}

export async function restartPipeline() {
    const response = await apiPost("/health/restart");

    if (!response.ok) {
        throw new Error("Failed to restart pipeline");
    }

    return response.json();
}

export async function savePipeline(localConfig: unknown) {
    const response = await apiPut("/health/config", {
        config: localConfig,
        restart_if_running: true,
    });

    if (!response.ok) {
        throw new Error("Failed to save config");
    }

    return response.json();
}
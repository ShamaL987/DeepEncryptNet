import type { FlowDaemonOverviewResponse } from "@/types/daemon";
import {API_BASE} from "@/api/index.ts";


export async function fetchOverview(): Promise<FlowDaemonOverviewResponse> {
    const response = await fetch(`${API_BASE}/health/overview`);

    if (!response.ok) {
        throw new Error("Failed to fetch daemon overview");
    }
    return response.json();
}

export async function startPipeline() {
    const response = await fetch(`${API_BASE}/health/start`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to start pipeline");
    return response.json();
}

export async function stopPipeline() {
    const response = await fetch(`${API_BASE}/health/stop`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to stop pipeline");
    return response.json();
}

export async function restartPipeline() {
    const response = await fetch(`${API_BASE}/health/restart`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to restart pipeline");
    return response.json();
}

export async function savePipeline(localConfig) {
    const response = await fetch(
        `${API_BASE}/health/config`, {
            method: "PUT",headers: {"Content-Type": "application/json"
            }, body: JSON.stringify({config: localConfig, restart_if_running: true}),});
    if (!response.ok) throw new Error("Failed to save config");
    return response.json();
}
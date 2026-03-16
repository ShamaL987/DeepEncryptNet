import type { FlowDaemonOverviewResponse } from "@/types/daemon";

const API_BASE = "http://localhost:8000/api/daemon";

export async function fetchOverview(): Promise<FlowDaemonOverviewResponse> {
    const response = await fetch(`${API_BASE}/overview`);

    if (!response.ok) {
        throw new Error("Failed to fetch daemon overview");
    }
    return response.json();
}

export async function startPipeline() {
    const response = await fetch(`${API_BASE}/start`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to start pipeline");
    return response.json();
}

export async function stopPipeline() {
    const response = await fetch(`${API_BASE}/stop`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to stop pipeline");
    return response.json();
}

export async function restartPipeline() {
    const response = await fetch(`${API_BASE}/restart`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to restart pipeline");
    return response.json();
}
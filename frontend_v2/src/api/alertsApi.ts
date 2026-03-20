import type { DashboardAlertsResponse } from "@/types/alerts.ts";
import { API_BASE } from "@/api/index.ts";

export async function fetchDashboardAlerts(): Promise<DashboardAlertsResponse> {
    const response = await fetch(`${API_BASE}/alerts-on/alerts`);

    if (!response.ok) {
        throw new Error("Failed to fetch dashboard alerts");
    }

    return response.json();
}
import type { DashboardOverviewApiResponse } from "@/types/dashboard";
import { API_BASE } from "@/api/index.ts";

export async function fetchDashboardOverview(): Promise<DashboardOverviewApiResponse> {
    const response = await fetch(`${API_BASE}/dashboard/overview`);

    if (!response.ok) {
        throw new Error("Failed to fetch dashboard overview");
    }

    return response.json();
}
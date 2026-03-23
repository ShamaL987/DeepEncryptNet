import type { DashboardOverviewApiResponse } from "@/types/dashboard";
import { apiGet } from "@/api/index.ts";

export async function fetchDashboardOverview(): Promise<DashboardOverviewApiResponse> {
    const response = await apiGet("/dashboard/overview");

    if (!response.ok) {
        throw new Error("Failed to fetch dashboard overview");
    }

    return response.json();
}
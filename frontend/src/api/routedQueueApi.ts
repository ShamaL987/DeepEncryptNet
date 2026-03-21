import type { RoutedQueueOverviewApiResponse } from "@/types/routedQueue";
import {API_BASE} from "@/api/index.ts";

export async function fetchRoutedQueueOverview(
    limit = 50
): Promise<RoutedQueueOverviewApiResponse> {
    const params = new URLSearchParams({
        limit: String(limit),
    });

    const response = await fetch(`${API_BASE}/routed/overview?${params.toString()}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (!response.ok) {
        throw new Error("Failed to fetch routed queue overview");
    }

    return response.json();
}
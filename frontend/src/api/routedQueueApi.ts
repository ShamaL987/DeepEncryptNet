import type { RoutedQueueOverviewApiResponse } from "@/types/routedQueue";
import { apiGet } from "@/api/index.ts";

export async function fetchRoutedQueueOverview(
    limit = 50,
): Promise<RoutedQueueOverviewApiResponse> {
    const params = new URLSearchParams({
        limit: String(limit),
    });

    const response = await apiGet(`/routed/overview?${params.toString()}`);

    if (!response.ok) {
        throw new Error("Failed to fetch routed queue overview");
    }

    return response.json();
}
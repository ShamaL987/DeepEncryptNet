import type {
    LiveFlowsOverviewApiResponse,
    LiveFlowsQueryParams,
} from "@/types/liveFlows";
import {API_BASE} from "@/api/index.ts";

function normalizeFilterValue(value: string): string {
    return value === "All" ? "all" : value;
}

export async function fetchLiveFlowsOverview(
    params: LiveFlowsQueryParams
): Promise<LiveFlowsOverviewApiResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set("limit", String(params.limit ?? 50));
    searchParams.set("decision", normalizeFilterValue(params.decision));
    searchParams.set("predicted_class", normalizeFilterValue(params.predictedClass));
    searchParams.set("reliability", normalizeFilterValue(params.reliability));
    searchParams.set("alerts_only", String(params.alertsOnly));

    const response = await fetch(`${API_BASE}/live-flows/overview?${searchParams.toString()}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });
    if (!response.ok) {
        throw new Error("Failed to fetch live flows overview");
    }

    return response.json();
}
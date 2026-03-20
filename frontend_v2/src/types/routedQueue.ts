export interface RoutedQueueItemApi {
    flow_id: string;
    timestamp: string;
    predicted_type: string;
    confidence: number;
    age_in_queue_sec: number;
    risk_status: string;
    total_packets: number;
    total_bytes: number;
    duration_sec: number | null;
}

export interface RoutedQueueGroupingSuggestionApi {
    label: string;
    count: number;
    nearest_class: string;
}

export interface RoutedQueueSummaryApi {
    queue_size: number;
    routed_per_min: number;
    avg_confidence: number | null;
    total_routed: number;
}

export interface RoutedQueueOverviewApiResponse {
    items: RoutedQueueItemApi[];
    grouping_suggestions: RoutedQueueGroupingSuggestionApi[];
    summary: RoutedQueueSummaryApi;
}

export type RoutedQueueReviewStatus = "New" | "In Review" | "Closed";

export interface RoutedFlowView {
    id: string;
    timestamp: string;
    predictedType: string;
    confidence: number;
    ageInQueue: string;
    reviewStatus: RoutedQueueReviewStatus;
    riskStatus: string;
    packets: number;
    bytes: number;
    duration: number | null;
}

export interface RoutedQueueGroupView {
    label: string;
    count: number;
    nearest: string;
}

export interface RoutedQueueKpiView {
    unknownQueueSize: number;
    routedPerMin: number;
    avgConfidence: string;
    totalRouted: number;
}

export interface RoutedQueuePageView {
    routedFlows: RoutedFlowView[];
    groups: RoutedQueueGroupView[];
    kpiData: RoutedQueueKpiView;
}
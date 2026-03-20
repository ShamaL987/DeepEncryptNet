export interface LiveFlowItemApi {
    flow_id: string;
    timestamp: string;
    src_to_dst: string;
    protocol: string;
    total_packets: number;
    total_bytes: number;
    duration_sec: number | null;
    predicted_type: string;
    confidence: number;
    decision: "Classified" | "Routed";
    reliability: "Reliable" | "Unreliable" | "Unknown";
    reason: string;
    model_version: string;
    age_sec: number;
    is_alert: boolean;
}

export interface LiveFlowsSummaryApi {
    total: number;
    classified: number;
    routed: number;
    reliable: number;
    unreliable: number;
    unknown: number;
    alerts: number;
}

export interface LiveFlowsFilterOptionsApi {
    decisions: string[];
    reliabilities: string[];
    predicted_classes: string[];
}

export interface LiveFlowsOverviewApiResponse {
    items: LiveFlowItemApi[];
    summary: LiveFlowsSummaryApi;
    filter_options: LiveFlowsFilterOptionsApi;
}

export interface LiveFlowsQueryParams {
    decision: string;
    predictedClass: string;
    reliability: string;
    alertsOnly: boolean;
    limit?: number;
}

export interface LiveFlowItemView {
    id: string;
    timestamp: string;
    srcToDst: string;
    protocol: string;
    packets: number;
    bytes: number;
    duration: number | null;
    predictedType: string;
    confidence: number;
    decision: "Classified" | "Routed";
    reliability: "Reliable" | "Unreliable" | "Unknown";
    reason: string;
    modelVersion: string;
    ageSec: number;
    isAlert: boolean;
}

export interface LiveFlowsFilterOptionsView {
    decisions: string[];
    predictedClasses: string[];
    reliabilities: string[];
}

export interface LiveFlowsOverviewView {
    items: LiveFlowItemView[];
    summary: LiveFlowsSummaryApi;
    filterOptions: LiveFlowsFilterOptionsView;
}
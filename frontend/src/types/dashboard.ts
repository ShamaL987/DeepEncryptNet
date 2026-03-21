export interface DashboardSummaryApi {
    uptime_sec: number | null;
    unique_flows: number;
    processed_per_min: number;
    predictions_per_min: number;
    prediction_total: number;
    classified_total: number;
    classified_percent: number;
    routed_total: number;
    routed_percent: number;
    queue_size: number;
    low_confidence_count: number;
    low_confidence_rate: number;
}

export interface DashboardFlowOverTimeApi {
    time: string;
    count: number;
}

export interface DashboardClassifiedVsRoutedApi {
    time: string;
    classified: number;
    routed: number;
}

export interface DashboardTrafficMixApi {
    label: string;
    count: number;
    percent: number;
}

export interface DashboardConfidenceDistributionApi {
    range: string;
    count: number;
}

export interface DashboardAlertApi {
    severity: string;
    title: string;
    message: string;
    timestamp: string;
}

export interface DashboardOverviewApiResponse {
    status: "running" | "stopped";
    is_running: boolean;
    pipeline_name: string | null;
    summary: DashboardSummaryApi;
    charts: {
        flows_over_time: DashboardFlowOverTimeApi[];
        classified_vs_routed: DashboardClassifiedVsRoutedApi[];
        traffic_mix: DashboardTrafficMixApi[];
        confidence_distribution: DashboardConfidenceDistributionApi[];
    };
    alerts: DashboardAlertApi[];
}

export interface DashboardAlertView {
    id: string;
    severity: string;
    title: string;
    message: string;
    timestamp: string;
}

export interface DashboardKpiView {
    uptime: string;
    uniqueFlows: number;
    processedPerMin: number;
    classifiedCount: number;
    classifiedPct: number;
    routedCount: number;
    routedPct: number;
    unknownQueueSize: number;
    lowConfidenceRate: number;
    lowConfidencePct: number;
}

export interface DashboardOverviewViewModel {
    status: "running" | "stopped";
    isRunning: boolean;
    pipelineName: string | null;
    kpiData: DashboardKpiView;
    flowsOverTime: {
        time: string;
        flows: number;
    }[];
    classifiedVsRouted: {
        time: string;
        classified: number;
        routed: number;
    }[];
    trafficMix: {
        name: string;
        value: number;
        percent: number;
    }[];
    confidenceDistribution: {
        range: string;
        count: number;
    }[];
    alerts: DashboardAlertView[];
}
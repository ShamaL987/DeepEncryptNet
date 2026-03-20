import type {
    DashboardOverviewApiResponse,
    DashboardOverviewViewModel,
} from "@/types/dashboard";

function formatUptime(seconds: number | null): string {
    if (seconds === null || seconds <= 0) {
        return "0s";
    }

    const totalSeconds = Math.floor(seconds);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }

    if (minutes > 0) {
        return `${minutes}m`;
    }

    return `${totalSeconds}s`;
}

export function mapDashboardOverviewToViewModel(
    data: DashboardOverviewApiResponse
): DashboardOverviewViewModel {
    return {
        status: data.status,
        isRunning: data.is_running,
        pipelineName: data.pipeline_name,
        kpiData: {
            uptime: formatUptime(data.summary.uptime_sec),
            uniqueFlows: data.summary.unique_flows,
            processedPerMin: data.summary.processed_per_min,
            classifiedCount: data.summary.classified_total,
            classifiedPct: data.summary.classified_percent,
            routedCount: data.summary.routed_total,
            routedPct: data.summary.routed_percent,
            unknownQueueSize: data.summary.queue_size,
            lowConfidenceRate: data.summary.low_confidence_count,
            lowConfidencePct: data.summary.low_confidence_rate,
        },
        flowsOverTime: data.charts.flows_over_time.map((item) => ({
            time: item.time,
            flows: item.count,
        })),
        classifiedVsRouted: data.charts.classified_vs_routed.map((item) => ({
            time: item.time,
            classified: item.classified,
            routed: item.routed,
        })),
        trafficMix: data.charts.traffic_mix.map((item) => ({
            name: item.label,
            value: item.count,
            percent: item.percent,
        })),
        confidenceDistribution: data.charts.confidence_distribution.map((item) => ({
            range: item.range,
            count: item.count,
        })),
        alerts: data.alerts.map((alert) => ({
            id: `${alert.title}-${alert.timestamp}`,
            severity: alert.severity,
            title: alert.title,
            message: alert.message,
            timestamp: alert.timestamp,
        })),
    };
}
import type {
    RoutedFlowView,
    RoutedQueueItemApi,
    RoutedQueueOverviewApiResponse,
    RoutedQueuePageView,
    RoutedQueueReviewStatus,
} from "@/types/routedQueue";

function formatAgeInQueue(ageInQueueSec: number): string {
    if (ageInQueueSec < 60) {
        return `${ageInQueueSec}s`;
    }

    const minutes = Math.floor(ageInQueueSec / 60);
    const seconds = ageInQueueSec % 60;

    if (minutes < 60) {
        return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

function mapRiskStatusToReviewStatus(riskStatus: string): RoutedQueueReviewStatus {
    const normalized = riskStatus.trim().toLowerCase();

    if (normalized.includes("high") || normalized.includes("critical")) {
        return "High Risk";
    }

    if (normalized.includes("low") || normalized.includes("benign")) {
        return "Medium Risk";
    }

    return "Low Risk";
}

function mapFlow(item: RoutedQueueItemApi): RoutedFlowView {
    return {
        id: item.flow_id,
        timestamp: item.timestamp,
        predictedType: item.predicted_type,
        confidence: Number(item.confidence.toFixed(2)),
        ageInQueue: formatAgeInQueue(item.age_in_queue_sec),
        reviewStatus: mapRiskStatusToReviewStatus(item.risk_status),
        riskStatus: item.risk_status,
        packets: item.total_packets,
        bytes: item.total_bytes,
        duration: item.duration_sec,
    };
}

export function mapRoutedQueueToPageView(
    response: RoutedQueueOverviewApiResponse
): RoutedQueuePageView {
    const routedFlows = response.items.map(mapFlow);

    return {
        routedFlows,
        groups: response.grouping_suggestions.map((group) => ({
            label: group.label,
            count: group.count,
            nearest: group.nearest_class,
        })),
        kpiData: {
            unknownQueueSize: response.summary.queue_size,
            routedPerMin: Number(response.summary.routed_per_min.toFixed(2)),
            avgConfidence:
                response.summary.avg_confidence !== null
                    ? response.summary.avg_confidence.toFixed(2)
                    : "N/A",
            totalRouted: response.summary.total_routed,
        },
    };
}
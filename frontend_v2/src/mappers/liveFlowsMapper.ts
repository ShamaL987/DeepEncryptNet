import type {
    LiveFlowItemApi,
    LiveFlowItemView,
    LiveFlowsOverviewApiResponse,
    LiveFlowsOverviewView,
} from "@/types/liveFlows";

function mapLiveFlowItem(item: LiveFlowItemApi): LiveFlowItemView {
    return {
        id: item.flow_id,
        timestamp: item.timestamp,
        srcToDst: item.src_to_dst,
        protocol: item.protocol,
        packets: item.total_packets,
        bytes: item.total_bytes,
        duration: item.duration_sec,
        predictedType: item.predicted_type,
        confidence: item.confidence,
        decision: item.decision,
        reliability: item.reliability,
        reason: item.reason,
        modelVersion: item.model_version,
        ageSec: item.age_sec,
        isAlert: item.is_alert,
    };
}

export function mapLiveFlowsOverviewToViewModel(
    response: LiveFlowsOverviewApiResponse
): LiveFlowsOverviewView {
    return {
        items: response.items.map(mapLiveFlowItem),
        summary: response.summary,
        filterOptions: {
            decisions: response.filter_options.decisions,
            predictedClasses: response.filter_options.predicted_classes,
            reliabilities: response.filter_options.reliabilities,
        },
    };
}
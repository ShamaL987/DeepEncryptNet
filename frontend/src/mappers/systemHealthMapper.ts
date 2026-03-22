import type { FlowDaemonOverviewResponse } from "@/types/daemon";

export interface PipelineConfig {
    ready_dir: string;
    processing_dir: string;
    processed_dir: string;
    streams_dir: string;
    max_packets: number;
    max_duration_sec: number;
    idle_timeout_sec: number;
    poll_interval_sec: number;
    auto_start: boolean;
    enable_stats: boolean;
    mode: string;
    feature_pipeline: string;
    system_delay: number;
    save_processed_batch_file: boolean;
    save_stream_files: boolean;
}

export interface SystemHealthViewModel {
    pipelineRunning: boolean;
    pipelineStatus: string;
    config: {
        ready_dir: string;
        processing_dir: string;
        processed_dir: string;
        streams_dir: string;
        max_packets: number;
        max_duration_sec: number;
        idle_timeout_sec: number;
        poll_interval_sec: number;
        auto_start: boolean;
        enable_stats: boolean;
        mode: string;
        feature_pipeline: string;
        system_delay: number;
    };
    healthCards: {
        flowsPerSec: number;
        predictionsPerSec: number;
        // featureLatencyAvg: number | null;
        // featureLatencyP95: number | null;
        inferenceLatencyAvg: number | null;
        inferenceLatencyP95: number | null;
        errors1h: number;
        errors24h: number;
        routed_percent: number;
        prediction_uptime_sec: number;
    };
    pipelineConfig: {
        pipelineName: string;
        pipelineVersion: string;
        temperatureT: number | null;
        useTemperatureForRouting: boolean;
        coverage: number | null;
        acceptedAccuracy: number | null;
        acceptedMacroF1: number | null;
    };
}

export function mapOverviewToViewModel(
    data: FlowDaemonOverviewResponse
): SystemHealthViewModel {
    return {
        pipelineRunning: data.is_running,
        pipelineStatus: data.status,
        config: {
            ...data.runtime_config.flow_daemon,
            system_delay: data.runtime_config.flow_daemon.timeout,
        },
        healthCards: {
            flowsPerSec: data.health.flows_per_sec,
            predictionsPerSec: data.health.predictions_per_sec,
            inferenceLatencyAvg: data.health.latest_flow_lag_ms,
            inferenceLatencyP95: data.health.flow_to_prediction_lag_avg_ms,
            // inferenceLatencyAvg: data.health.latest_prediction_lag_ms,
            // inferenceLatencyP95: data.health.flow_to_prediction_lag_p95_ms,
            errors1h: 0,
            errors24h: 0,
            routed_percent: data.health.routed_percent,
            prediction_uptime_sec: data.health.prediction_uptime_sec
        },
        pipelineConfig: {
            pipelineName: data.pipline_config.pipeline_name,
            pipelineVersion: data.pipline_config.pipeline_version,
            temperatureT: data.pipline_config.temperature_T,
            useTemperatureForRouting: data.pipline_config.use_temperature_for_routing,
            coverage: data.pipline_config.coverage,
            acceptedAccuracy: data.pipline_config.accepted_accuracy,
            acceptedMacroF1: data.pipline_config.accepted_macro_f1,
        },
    };
}
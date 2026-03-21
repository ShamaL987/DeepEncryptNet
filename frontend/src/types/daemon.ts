
export interface FlowDaemonOverviewResponse {
    status: string;
    is_running: boolean;
    runtime_config: {
        flow_daemon: {
            ready_dir: string;
            processing_dir: string;
            processed_dir: string;
            streams_dir: string;
            max_packets: number;
            max_duration_sec: number;
            auto_start: boolean;
            mode: string;
            idle_timeout_sec: number;
            poll_interval_sec: number;
            enable_stats: boolean;
            feature_pipeline: string;
            timeout: number;
        };
    };
    health: {
        flows_per_sec: number;
        predictions_per_sec: number;
        latest_flow_lag_ms: number | null;
        latest_prediction_lag_ms: number | null;
        flow_to_prediction_lag_avg_ms: number | null;
        flow_to_prediction_lag_p95_ms: number | null;
        confidence_avg: number | null;
        confidence_p95: number | null;
        accepted_count: number;
        routed_count: number;
        routed_percent: number;
        prediction_uptime_sec: number;
    };
    pipline_config: {
        pipeline_name: string;
        pipeline_version: string;
        temperature_T: number | null;
        use_temperature_for_routing: boolean;
        coverage: number | null;
        accepted_accuracy: number | null;
        accepted_macro_f1: number | null;
    };
}

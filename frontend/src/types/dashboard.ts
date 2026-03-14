export interface Status {
  running: boolean
  uptime_sec: number | null
  flows_processed: number
  last_update: string | null
}

export interface ClassDistribution {
  window_sec: number
  total: number
  distribution: Record<string, number>
}

export interface RoutingSummary {
  window_sec: number
  classified: number
  routed: number
  route_rate: number
}

export interface ConfidenceEntropy {
  window_sec: number
  avg_confidence: number | null
  avg_entropy: number | null
}

export interface RecentFlow {
  flow_id: string
  start_ts: number
  end_ts: number
  duration_sec: number
  size_bytes: number
  predicted_class: string
  action: 'CLASSIFY' | 'ROUTE'
  confidence: number
  entropy: number
  created_at: string
}

export interface DaemonStats {
  window_sec: number
  packets_per_sec: number
  flows_per_sec: number
  feature_latency_ms_avg: number | null
  inference_latency_ms_avg: number | null
  confidence_median: number | null
  route_rate: number
  error_count: number
}

export interface DaemonStatus {
  running: boolean
  config: Record<string, unknown>
  timestamp: string
  stats: DaemonStats
}

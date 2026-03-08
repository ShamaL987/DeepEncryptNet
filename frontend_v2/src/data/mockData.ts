// ============================================================
// DeepEncryptNet — Mock Data
// ============================================================

export type Decision = "Classified" | "Routed";
export type Reliability = "Reliable" | "Unreliable" | "Unknown";
export type ReviewStatus = "New" | "In Review" | "Closed";
export type PipelineStage = "Capture" | "Ingestion" | "Feature Extraction" | "Inference";
export type StageStatus = "OK" | "Degraded" | "Down";

export interface Flow {
  id: string;
  timestamp: string;
  src: string;
  dst: string;
  protocol: string;
  packets: number;
  bytes: number;
  duration: number;
  predictedType: string;
  confidence: number;
  decision: Decision;
  reliability: Reliability;
  reason: string;
  modelVersion: string;
  // stats
  avgPktSize: number;
  pktRateMean: number;
  pktRateStd: number;
  byteRateMean: number;
  byteRateStd: number;
  burstCount: number;
  burstAvgLength: number;
  // routed queue extras
  routedAt?: string;
  ageInQueue?: string;
  reviewStatus?: ReviewStatus;
}

export interface Alert {
  id: string;
  type: "routing_spike" | "low_confidence" | "queue_growing";
  title: string;
  message: string;
  severity: "warning" | "error";
  timestamp: string;
}

const trafficTypes = ["Browsing", "Streaming", "File Transfer", "VoIP", "Download", "Email", "Chat"];
const protocols = ["TLS 1.3", "TLS 1.2", "QUIC", "DTLS", "TCP/TLS"];

function ip() {
  return `${10 + Math.floor(Math.random() * 240)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`;
}

function flowId(i: number) {
  return `FLW-${String(i).padStart(6, "0")}`;
}

function randomBetween(a: number, b: number) {
  return a + Math.random() * (b - a);
}

function generateFlow(i: number): Flow {
  const confidence = Math.round(randomBetween(0.15, 0.99) * 100) / 100;
  const T_low = 0.5;
  const T_high = 0.75;
  const isRouted = confidence < T_low || Math.random() < 0.12;
  const decision: Decision = isRouted ? "Routed" : "Classified";
  let reliability: Reliability;
  if (isRouted) reliability = "Unknown";
  else if (confidence >= T_high) reliability = "Reliable";
  else reliability = "Unreliable";

  let reason: string;
  if (isRouted) reason = `Confidence below threshold (${confidence} < ${T_low}) → routed`;
  else if (reliability === "Unreliable") reason = `Classified with moderate confidence (${confidence}) → marked unreliable`;
  else reason = `High confidence classification (${confidence})`;

  const dur = Math.round(randomBetween(0.5, 120) * 10) / 10;
  const pkts = Math.floor(randomBetween(10, 5000));
  const byts = Math.floor(randomBetween(500, 5000000));

  const now = new Date();
  const ts = new Date(now.getTime() - Math.floor(Math.random() * 3600000));

  const flow: Flow = {
    id: flowId(i),
    timestamp: ts.toISOString(),
    src: `${ip()}:${1024 + Math.floor(Math.random() * 50000)}`,
    dst: `${ip()}:${[443, 8443, 993, 5061, 3478][Math.floor(Math.random() * 5)]}`,
    protocol: protocols[Math.floor(Math.random() * protocols.length)],
    packets: pkts,
    bytes: byts,
    duration: dur,
    predictedType: trafficTypes[Math.floor(Math.random() * trafficTypes.length)],
    confidence,
    decision,
    reliability,
    reason,
    modelVersion: "v2.4.1",
    avgPktSize: Math.round(byts / pkts),
    pktRateMean: Math.round((pkts / Math.max(dur, 0.1)) * 100) / 100,
    pktRateStd: Math.round(randomBetween(1, 50) * 100) / 100,
    byteRateMean: Math.round((byts / Math.max(dur, 0.1)) * 100) / 100,
    byteRateStd: Math.round(randomBetween(100, 50000) * 100) / 100,
    burstCount: Math.floor(randomBetween(0, 15)),
    burstAvgLength: Math.round(randomBetween(1, 30) * 10) / 10,
  };

  if (isRouted) {
    const queueMinutes = Math.floor(randomBetween(1, 180));
    flow.routedAt = ts.toISOString();
    flow.ageInQueue = queueMinutes < 60 ? `${queueMinutes}m` : `${Math.floor(queueMinutes / 60)}h ${queueMinutes % 60}m`;
    flow.reviewStatus = (["New", "In Review", "Closed"] as ReviewStatus[])[Math.floor(Math.random() * 3)];
  }

  return flow;
}

// Generate 200 flows
export const mockFlows: Flow[] = Array.from({ length: 200 }, (_, i) => generateFlow(i + 1));

export const classifiedFlows = mockFlows.filter(f => f.decision === "Classified");
export const routedFlows = mockFlows.filter(f => f.decision === "Routed");

// KPI data
export const kpiData = {
  uptime: "14d 7h 23m",
  uniqueFlows: mockFlows.length,
  processedPerMin: 847,
  classifiedCount: classifiedFlows.length,
  classifiedPct: Math.round((classifiedFlows.length / mockFlows.length) * 100),
  routedCount: routedFlows.length,
  routedPct: Math.round((routedFlows.length / mockFlows.length) * 100),
  unknownQueueSize: routedFlows.filter(f => f.reviewStatus !== "Closed").length,
  lowConfidenceRate: mockFlows.filter(f => f.confidence < 0.5).length,
  lowConfidencePct: Math.round((mockFlows.filter(f => f.confidence < 0.5).length / mockFlows.length) * 100),
};

// Pipeline status
export const pipelineStatus: { stage: PipelineStage; status: StageStatus }[] = [
  { stage: "Capture", status: "OK" },
  { stage: "Ingestion", status: "OK" },
  { stage: "Feature Extraction", status: "OK" },
  { stage: "Inference", status: "Degraded" },
];

// Time series data for charts
export const flowsOverTime = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, "0")}:00`,
  flows: Math.floor(randomBetween(400, 1200)),
}));

export const classifiedVsRouted = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, "0")}:00`,
  classified: Math.floor(randomBetween(350, 1000)),
  routed: Math.floor(randomBetween(30, 200)),
}));

export const trafficMix = trafficTypes.map(type => ({
  name: type,
  value: Math.floor(randomBetween(5, 30)),
}));

export const confidenceDistribution = [
  { range: "0.0-0.1", count: 3 },
  { range: "0.1-0.2", count: 7 },
  { range: "0.2-0.3", count: 12 },
  { range: "0.3-0.4", count: 18 },
  { range: "0.4-0.5", count: 15 },
  { range: "0.5-0.6", count: 22 },
  { range: "0.6-0.7", count: 28 },
  { range: "0.7-0.8", count: 38 },
  { range: "0.8-0.9", count: 35 },
  { range: "0.9-1.0", count: 22 },
];

export const alerts: Alert[] = [
  {
    id: "alert-1",
    type: "routing_spike",
    title: "Routing Spike Detected",
    message: "Routed % exceeded 35% for the last 10 minutes (currently 41%)",
    severity: "error",
    timestamp: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: "alert-2",
    type: "low_confidence",
    title: "Low Confidence Surge",
    message: "Confidence median dropped from 0.78 to 0.62 in the last 15 minutes",
    severity: "warning",
    timestamp: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: "alert-3",
    type: "queue_growing",
    title: "Unknown Queue Growing",
    message: "Queue size increased by 24 flows in the last 5 minutes",
    severity: "warning",
    timestamp: new Date(Date.now() - 180000).toISOString(),
  },
];

// System health data
export const systemHealth = {
  captureRate: 12847,
  flowCreationRate: 847,
  featureExtractorLatency: { avg: 2.3, p95: 8.1 },
  inferenceLatency: { avg: 4.7, p95: 15.2 },
  errors1h: 3,
  errors24h: 17,
  modelVersion: "v2.4.1",
  dataset: "ISCX VPN-NonVPN 2016",
  tLow: 0.5,
  tHigh: 0.75,
  calibration: "Temperature Scaling (τ = 1.42)",
};

export const confidenceTrend = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, "0")}:00`,
  median: Math.round(randomBetween(0.6, 0.82) * 100) / 100,
}));

export const routedPctTrend = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, "0")}:00`,
  pct: Math.round(randomBetween(12, 42) * 10) / 10,
}));

// Flow detail behavior time series
export function generateFlowBehavior(duration: number) {
  const points = Math.min(Math.max(Math.floor(duration * 2), 10), 60);
  return Array.from({ length: points }, (_, i) => ({
    time: Math.round((i / points) * duration * 100) / 100,
    packetsPerSec: Math.floor(randomBetween(5, 200)),
    bytesPerSec: Math.floor(randomBetween(500, 100000)),
  }));
}

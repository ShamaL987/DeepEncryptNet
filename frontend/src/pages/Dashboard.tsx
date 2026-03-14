import { useMemo, useState } from 'react'
import {
  fetchClassDistribution,
  fetchConfidence,
  fetchDaemonStatus,
  fetchRecentFlows,
  fetchRoutingSummary,
  fetchStatus,
  postDaemonConfig,
  restartDaemon,
  startDaemon,
  stopDaemon,
} from '../api/dashboardApi'
import { usePolling } from '../hooks/usePolling'
import {
  ClassDistribution,
  ConfidenceEntropy,
  DaemonStatus,
  RecentFlow,
  RoutingSummary,
  Status,
} from '../types/dashboard'
import StatCard from '../ui/StatCard'
import TabBar from '../ui/TabBar'
import AlertBanner from '../ui/AlertBanner'
import AnimatedView from '../ui/AnimatedView'
import RecentFlowsTable from '../components/RecentFlowsTable'
import RoutingSummaryView from '../components/RoutingSummary'
import ClassDistributionView from '../components/ClassDistribution'

const TABS = ['Dashboard', 'Live Flows', 'Routed Queue', 'System Health'] as const

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('Dashboard')
  const [windowSec, setWindowSec] = useState(60)

  const [status, setStatus] = useState<Status | null>(null)
  const [classDistribution, setClassDistribution] = useState<ClassDistribution | null>(null)
  const [routingSummary, setRoutingSummary] = useState<RoutingSummary | null>(null)
  const [confidence, setConfidence] = useState<ConfidenceEntropy | null>(null)
  const [recentFlows, setRecentFlows] = useState<RecentFlow[]>([])
  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [configForm, setConfigForm] = useState({
    poll_interval_sec: '1.0',
    idle_timeout_sec: '30',
    max_packets: '100',
    max_duration_sec: '20',
    enable_stats: true,
  })

  const applyDaemonConfig = async () => {
    await postDaemonConfig({
      poll_interval_sec: Number(configForm.poll_interval_sec),
      idle_timeout_sec: Number(configForm.idle_timeout_sec),
      max_packets: Number(configForm.max_packets),
      max_duration_sec: Number(configForm.max_duration_sec),
      enable_stats: configForm.enable_stats,
    })
  }

  usePolling(async () => {
    try {
      const [s, cls, r, conf, flows, daemon] = await Promise.all([
        fetchStatus(),
        fetchClassDistribution(windowSec),
        fetchRoutingSummary(windowSec),
        fetchConfidence(windowSec),
        fetchRecentFlows(100),
        fetchDaemonStatus(windowSec),
      ])

      setStatus(s)
      setClassDistribution(cls)
      setRoutingSummary(r)
      setConfidence(conf)
      setRecentFlows(flows)
      setDaemonStatus(daemon)
      setError(null)

      const cfg = daemon.config as Record<string, unknown>
      setConfigForm(prev => ({
        ...prev,
        poll_interval_sec: String(cfg.poll_interval_sec ?? prev.poll_interval_sec),
        idle_timeout_sec: String(cfg.idle_timeout_sec ?? prev.idle_timeout_sec),
        max_packets: String(cfg.max_packets ?? prev.max_packets),
        max_duration_sec: String(cfg.max_duration_sec ?? prev.max_duration_sec),
        enable_stats: Boolean(cfg.enable_stats ?? prev.enable_stats),
      }))
    } catch (e) {
      setError((e as Error).message)
    }
  }, 3000, [windowSec])

  const routedRows = useMemo(
    () => recentFlows.filter(flow => flow.action === 'ROUTE'),
    [recentFlows],
  )

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginBottom: 16 }}>DeepEncryptNet Control Plane</h1>

      {error && <AlertBanner level="error">Backend fetch failed: {error}</AlertBanner>}

      <TabBar
        tabs={TABS as unknown as string[]}
        active={activeTab}
        onChange={(tab: string) => setActiveTab(tab as (typeof TABS)[number])}
      />

      <div style={{ marginBottom: 16 }}>
        <label>Window (sec): </label>
        <select value={windowSec} onChange={e => setWindowSec(Number(e.target.value))}>
          <option value={60}>60</option>
          <option value={300}>300</option>
          <option value={900}>900</option>
        </select>
      </div>

      <AnimatedView show={activeTab === 'Dashboard'}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
          <StatCard label="Flows Processed" value={status?.flows_processed?.toString() ?? '—'} />
          <StatCard label="Packets/sec" value={daemonStatus ? daemonStatus.stats.packets_per_sec.toFixed(2) : '—'} />
          <StatCard label="Flows/sec" value={daemonStatus ? daemonStatus.stats.flows_per_sec.toFixed(2) : '—'} />
          <StatCard label="Routed %" value={routingSummary ? `${(routingSummary.route_rate * 100).toFixed(1)}%` : '—'} />
        </div>
        {classDistribution && <ClassDistributionView data={classDistribution} />}
        {routingSummary && <RoutingSummaryView data={routingSummary} />}
      </AnimatedView>

      <AnimatedView show={activeTab === 'Live Flows'}>
        <RecentFlowsTable rows={recentFlows} />
      </AnimatedView>

      <AnimatedView show={activeTab === 'Routed Queue'}>
        <RecentFlowsTable rows={routedRows} />
      </AnimatedView>

      <AnimatedView show={activeTab === 'System Health'}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
          <StatCard label="Daemon" value={daemonStatus?.running ? 'Running' : 'Stopped'} />
          <StatCard
            label="Feature Latency (ms)"
            value={daemonStatus?.stats.feature_latency_ms_avg?.toFixed(2) ?? '—'}
          />
          <StatCard
            label="Inference Latency (ms)"
            value={daemonStatus?.stats.inference_latency_ms_avg?.toFixed(2) ?? '—'}
          />
          <StatCard
            label="Confidence Median"
            value={daemonStatus?.stats.confidence_median?.toFixed(3) ?? '—'}
          />
          <StatCard label="Errors" value={daemonStatus?.stats.error_count?.toString() ?? '0'} />
          <StatCard
            label="Route Trend"
            value={daemonStatus ? `${(daemonStatus.stats.route_rate * 100).toFixed(1)}%` : '—'}
          />
        </div>

        {confidence && (
          <p>
            Confidence avg: {confidence.avg_confidence?.toFixed(3) ?? '—'} | Entropy avg:{' '}
            {confidence.avg_entropy?.toFixed(3) ?? '—'}
          </p>
        )}

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button onClick={() => startDaemon()}>Start</button>
          <button onClick={() => stopDaemon()}>Stop</button>
          <button onClick={() => restartDaemon()}>Restart</button>
        </div>

        <h3>Daemon Config</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(180px, 280px))', gap: 12 }}>
          <label>
            Poll interval (sec)
            <input
              value={configForm.poll_interval_sec}
              onChange={e => setConfigForm(v => ({ ...v, poll_interval_sec: e.target.value }))}
            />
          </label>
          <label>
            Idle timeout (sec)
            <input
              value={configForm.idle_timeout_sec}
              onChange={e => setConfigForm(v => ({ ...v, idle_timeout_sec: e.target.value }))}
            />
          </label>
          <label>
            Max packets
            <input
              value={configForm.max_packets}
              onChange={e => setConfigForm(v => ({ ...v, max_packets: e.target.value }))}
            />
          </label>
          <label>
            Max duration (sec)
            <input
              value={configForm.max_duration_sec}
              onChange={e => setConfigForm(v => ({ ...v, max_duration_sec: e.target.value }))}
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={configForm.enable_stats}
              onChange={e => setConfigForm(v => ({ ...v, enable_stats: e.target.checked }))}
            />
            Enable stats extraction
          </label>
        </div>

        <div style={{ marginTop: 12 }}>
          <button onClick={applyDaemonConfig}>Save Config</button>
        </div>
      </AnimatedView>
    </div>
  )
}

export default Dashboard

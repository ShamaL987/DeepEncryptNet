const API_BASE = '/api'

const json = async (url: string) => {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const fetchStatus = async () => json(`${API_BASE}/status`)
export const fetchClassDistribution = async (windowSec = 60) =>
  json(`${API_BASE}/analytics/classes?window_sec=${windowSec}`)
export const fetchRoutingSummary = async (windowSec = 60) =>
  json(`${API_BASE}/analytics/routing?window_sec=${windowSec}`)
export const fetchClassifiedDistribution = async (windowSec = 60) =>
  json(`${API_BASE}/analytics/classified?window_sec=${windowSec}`)
export const fetchRoutedDistribution = async (windowSec = 60) =>
  json(`${API_BASE}/analytics/routed?window_sec=${windowSec}`)
export const fetchConfidence = async (windowSec = 120) =>
  json(`${API_BASE}/analytics/confidence?window_sec=${windowSec}`)
export const fetchRecentFlows = async (limit = 50) =>
  json(`${API_BASE}/flows/recent?limit=${limit}`)

export const fetchDaemonStatus = async (windowSec = 60) =>
  json(`${API_BASE}/daemon/status?window_sec=${windowSec}`)

export const fetchDaemonConfig = async () =>
  json(`${API_BASE}/daemon/config`)

export const postDaemonConfig = async (payload: Record<string, unknown>) => {
  const r = await fetch(`${API_BASE}/daemon/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const startDaemon = async () => {
  const r = await fetch(`${API_BASE}/daemon/start`, { method: 'POST' })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const stopDaemon = async () => {
  const r = await fetch(`${API_BASE}/daemon/stop`, { method: 'POST' })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const restartDaemon = async () => {
  const r = await fetch(`${API_BASE}/daemon/restart`, { method: 'POST' })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

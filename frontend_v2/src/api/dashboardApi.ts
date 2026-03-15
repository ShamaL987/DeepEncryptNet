const API_BASE = 'api'

export const fetchStatus = async () =>
    fetch(`${API_BASE}/status`).then(r => r.json())

export const fetchClassDistribution = async (windowSec = 60) =>
    fetch(`${API_BASE}/analytics/classes?window_sec=${windowSec}`).then(r => r.json())

export const fetchRoutingSummary = async (windowSec = 60) =>
    fetch(`${API_BASE}/analytics/routing?window_sec=${windowSec}`).then(r => r.json())

export const fetchConfidence = async (windowSec = 120) =>
    fetch(`${API_BASE}/analytics/confidence?window_sec=${windowSec}`).then(r => r.json())

export const fetchRecentFlows = async (limit = 50) =>
    fetch(`${API_BASE}/flows/recent?limit=${limit}`).then(r => r.json())

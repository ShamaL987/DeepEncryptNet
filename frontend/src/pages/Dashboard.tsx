import { useState } from 'react'
import {
    fetchStatus,
    fetchClassDistribution,
    fetchRoutingSummary,
    fetchRecentFlows
} from '../api/dashboardApi'
import { usePolling } from '../hooks/usePolling'
import {
    Status,
    ClassDistribution,
    RoutingSummary,
    RecentFlow
} from '../types/dashboard'

import StatusBar from '../components/StatusBar'
import ClassDistributionView from '../components/ClassDistribution'
import RoutingSummaryView from '../components/RoutingSummary'
import RecentFlowsTable from '../components/RecentFlowsTable'

import StatCard from '../ui/StatCard'
import AlertBanner from '../ui/AlertBanner'
import TabBar from '../ui/TabBar'
import AnimatedView from '../ui/AnimatedView'

const TABS = ['Overview', 'Analytics', 'Flows'] as const
type Tab = typeof TABS[number]

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState<Tab>('Overview')

    const [status, setStatus] = useState<Status | null>(null)
    const [classes, setClasses] = useState<ClassDistribution | null>(null)
    const [routing, setRouting] = useState<RoutingSummary | null>(null)
    const [flows, setFlows] = useState<RecentFlow[]>([])

    usePolling(async () => {
        setStatus(await fetchStatus())
        setClasses(await fetchClassDistribution(60))
        setRouting(await fetchRoutingSummary(60))
        setFlows(await fetchRecentFlows(50))
    }, 3000)

    const showAlert =
        routing && routing.route_rate > 0.25

    return (
        <div style={{ padding: 24 }}>
            <h1 style={{ marginBottom: 16 }}>DeepEncryptNet Dashboard</h1>

            <TabBar
                tabs={TABS as unknown as string[]}
                active={activeTab}
                onChange={(t: string) => setActiveTab(t as Tab)}
            />

            {showAlert && (
                <AlertBanner level="warning">
                    High routing rate detected — possible unknown or tunneled traffic.
                </AlertBanner>
            )}

            <AnimatedView show={activeTab === 'Overview'}>
                {status && routing && (
                    <div
                        style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(4, 1fr)',
                            gap: 16,
                            marginBottom: 24
                        }}
                    >
                        <StatCard
                            label="Uptime (s)"
                            value={status.uptime_sec ? status.uptime_sec.toFixed(0) : '—'}
                        />
                        <StatCard
                            label="Flows Processed"
                            value={status.flows_processed.toString()}
                        />
                        <StatCard
                            label="Classified"
                            value={routing.classified.toString()}
                        />
                        <StatCard
                            label="Routed %"
                            value={`${(routing.route_rate * 100).toFixed(1)}%`}
                        />
                    </div>
                )}

                {status && <StatusBar data={status} />}
            </AnimatedView>

            <AnimatedView show={activeTab === 'Analytics'}>
                {classes && <ClassDistributionView data={classes} />}
                {routing && <RoutingSummaryView data={routing} />}
            </AnimatedView>

            <AnimatedView show={activeTab === 'Flows'}>
                <RecentFlowsTable rows={flows} />
            </AnimatedView>
        </div>
    )
}

export default Dashboard

import GlassCard from './GlassCard'
import { ReactNode } from 'react'

type Props = {
    level: 'info' | 'warning' | 'critical'
    children: ReactNode
}

const COLORS = {
    info: '#4da3ff',
    warning: '#ffb020',
    critical: '#ff4d4f'
}

const AlertBanner = ({ level, children }: Props) => {
    return (
        <GlassCard
            style={{
                borderLeft: `4px solid ${COLORS[level]}`,
                marginBottom: 20
            }}
        >
            <div style={{ color: COLORS[level], fontWeight: 500 }}>
                {children}
            </div>
        </GlassCard>
    )
}

export default AlertBanner

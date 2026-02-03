import GlassCard from '../ui/GlassCard'
import ThreatBadge from '../ui/ThreatBadge'
import { deriveThreat } from '../utils/threat'
import { RecentFlow } from '../types/dashboard'

type Props = {
    rows: RecentFlow[]
}

const RecentFlowsTable = ({ rows }: Props) => (
    <GlassCard>
        <table width="100%" style={{ borderCollapse: 'collapse' }}>
            <thead>
            <tr style={{ textAlign: 'left', fontSize: 12, opacity: 0.7 }}>
                <th>Flow</th>
                <th>Class</th>
                <th>Entropy</th>
                <th>Threat</th>
            </tr>
            </thead>

            <tbody>
            {rows.map(r => {
                const threat = deriveThreat(
                    r.action,
                    r.entropy,
                    r.confidence
                )

                return (
                    <tr key={r.flow_id} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                        <td>{r.flow_id.slice(0, 8)}</td>
                        <td>{r.predicted_class}</td>
                        <td>{r.entropy.toFixed(2)}</td>
                        <td>
                            <ThreatBadge level={threat} />
                        </td>
                    </tr>
                )
            })}
            </tbody>
        </table>
    </GlassCard>
)

export default RecentFlowsTable

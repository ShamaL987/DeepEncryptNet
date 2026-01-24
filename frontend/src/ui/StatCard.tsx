import GlassCard from './GlassCard'

type Props = {
    label: string
    value: string
}

const StatCard = ({ label, value }: Props) => {
    return (
        <GlassCard>
            <div style={{ fontSize: 12, opacity: 0.7 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>
                {value}
            </div>
        </GlassCard>
    )
}

export default StatCard

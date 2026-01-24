import { ThreatLevel } from '../utils/threat'

const COLORS: Record<ThreatLevel, string> = {
    NORMAL: '#2ecc71',     // green
    ELEVATED: '#f1c40f',   // yellow
    HIGH: '#e74c3c'        // red
}

type Props = {
    level: ThreatLevel
}

const ThreatBadge = ({ level }: Props) => {
    return (
        <span
            style={{
                padding: '4px 10px',
                borderRadius: 999,
                background: COLORS[level],
                color: '#000',
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: 0.5
            }}
        >
      {level}
    </span>
    )
}

export default ThreatBadge

import { ReactNode } from 'react'

type Props = {
    children: ReactNode
    style?: React.CSSProperties
}

const GlassCard = ({ children, style }: Props) => {
    return (
        <div
            style={{
                background: 'rgba(20, 20, 25, 0.65)',
                backdropFilter: 'blur(14px)',
                WebkitBackdropFilter: 'blur(14px)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 18,
                padding: 20,
                boxShadow: '0 10px 30px rgba(0,0,0,0.4)',
                transition: 'all 0.25s ease',
                ...style
            }}
        >
            {children}
        </div>
    )
}

export default GlassCard

import { ReactNode } from 'react'

type Props = {
    show: boolean
    children: ReactNode
}

const AnimatedView = ({ show, children }: Props) => {
    return (
        <div
            style={{
                opacity: show ? 1 : 0,
                transform: show ? 'translateY(0)' : 'translateY(10px)',
                pointerEvents: show ? 'auto' : 'none',
                transition: 'all 0.35s ease',
                marginBottom: show ? 24 : 0
            }}
        >
            {show && children}
        </div>
    )
}

export default AnimatedView

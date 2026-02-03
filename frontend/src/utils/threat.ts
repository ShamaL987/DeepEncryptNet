export type ThreatLevel = 'NORMAL' | 'ELEVATED' | 'HIGH'

export type FlowAction = 'CLASSIFY' | 'ROUTE'

export const deriveThreat = (
    action: FlowAction,
    entropy: number,
    confidence: number
): ThreatLevel => {
    if (action === 'ROUTE') {
        if (entropy >= 1.5 || confidence <= 0.5) {
            return 'HIGH'
        }
        return 'ELEVATED'
    }

    return 'NORMAL'
}

import { RoutingSummary } from '../types/dashboard'

const RoutingSummaryView = ({ data }: { data: RoutingSummary }) => (
    <div>
        <h3>Routing Summary</h3>
        Classified: {data.classified} |
        Routed: {data.routed} |
        Rate: {(data.route_rate * 100).toFixed(1)}%
    </div>
)

export default RoutingSummaryView

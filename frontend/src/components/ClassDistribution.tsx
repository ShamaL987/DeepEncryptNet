import { ClassDistribution } from '../types/dashboard'

const ClassDistributionView = ({ data }: { data: ClassDistribution }) => (
    <div>
        <h3>Class Distribution (last {data.window_sec}s)</h3>
        <ul>
            {Object.entries(data.distribution).map(([k, v]) => (
                <li key={k}>{k}: {v}</li>
            ))}
        </ul>
    </div>
)

export default ClassDistributionView

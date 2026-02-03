import { Status } from '../types/dashboard'

const StatusBar = ({ data }: { data: Status }) => (
    <div>
        <strong>Status:</strong> {data.running ? 'Running' : 'Stopped'} |
        Uptime: {data.uptime_sec?.toFixed(1)}s |
        Total flows: {data.flows_processed}
    </div>
)

export default StatusBar

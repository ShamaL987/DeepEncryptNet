export interface DashboardAlertApi {
    id: string;
    severity: string;
    title: string;
    message: string;
    timestamp: string;
}

export interface DashboardAlertsResponse {
    items: DashboardAlertApi[];
    count: number;
    has_alerts: boolean;
    generated_at: string;
}
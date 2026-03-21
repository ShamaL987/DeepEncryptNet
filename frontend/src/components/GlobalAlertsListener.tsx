import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { usePolling } from "@/hooks/usePolling";
import { fetchDashboardAlerts } from "@/api/alertsApi";

export function GlobalAlertsListener() {
    const navigate = useNavigate();
    const notifiedAlertIdsRef = useRef<Set<string>>(new Set());

    const fetchAlertsStable = useCallback(() => fetchDashboardAlerts(), []);
    const { data } = usePolling(fetchAlertsStable, 30000);

    const alerts = useMemo(() => {
        return data?.items ?? [];
    }, [data?.items]);

    useEffect(() => {
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }
    }, []);

    useEffect(() => {
        if (alerts.length === 0) {
            return;
        }

        const newAlerts = alerts.filter(
            (alert) => !notifiedAlertIdsRef.current.has(alert.id)
        );

        newAlerts.forEach((alert, index) => {
            notifiedAlertIdsRef.current.add(alert.id);

            setTimeout(() => {
                toast(alert.title, {
                    description: alert.message,
                    duration: 8000,
                    icon:
                        alert.severity === "error" || alert.severity === "high" ? "🔴" : "🟡",
                    action: {
                        label: "View",
                        onClick: () => navigate("/dashboard"),
                    },
                });

                if ("Notification" in window && Notification.permission === "granted") {
                    const notification = new Notification(`⚠ ${alert.title}`, {
                        body: alert.message,
                        icon: "/placeholder.svg",
                        tag: alert.id,
                    });

                    notification.onclick = () => {
                        window.focus();
                        navigate("/dashboard");
                    };
                }
            }, index * 1200);
        });
    }, [alerts, navigate]);

    return null;
}
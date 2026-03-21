import { Outlet } from "react-router-dom";
import { GlobalAlertsListener } from "@/components/GlobalAlertsListener";


export function Layout() {
    return (
        <div className="min-h-screen bg-background">
            <GlobalAlertsListener />
            {/* existing sidebar / topbar / content */}
            <Outlet />
        </div>
    );
}
import { Navigate, Outlet } from "react-router-dom";
import { getAuthSession } from "@/api/login.ts";

export function PublicRoute() {
    const session = getAuthSession();

    if (session) {
        return <Navigate to="/dashboard" replace />;
    }

    return <Outlet />;
}
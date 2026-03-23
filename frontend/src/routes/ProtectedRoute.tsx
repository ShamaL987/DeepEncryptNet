import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAuthSession } from "@/api/login.ts";

export function ProtectedRoute() {
    const location = useLocation();
    const session = getAuthSession();

    if (!session) {
        return <Navigate to="/login" replace state={{ from: location }} />;
    }

    return <Outlet />;
}
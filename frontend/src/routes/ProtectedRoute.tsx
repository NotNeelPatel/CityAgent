import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import type { AppRole } from "@/context/AuthContext";

export function ProtectedRoute({
  allow,
}: {
  allow?: AppRole[];
}) {
  const { user, role, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // Role check (only if allow is provided)
  if (allow && (!role || !allow.includes(role))) {
    return <Navigate to="/search" replace />;
  }

  return <Outlet />;
}

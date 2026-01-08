import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export function PublicRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  if (user) {
    return <Navigate to="/search" replace />;
  }

  return <Outlet />;
}

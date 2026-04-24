import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import type { Role } from "../../types";

function fallbackPathForRole(role: Role): string {
  if (role === "trainer") return "/assessments";
  if (role === "salesperson") return "/crm";
  if (role === "receptionist") return "/dashboard/operational";
  return "/dashboard/executive";
}

export function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: Role[] }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        Carregando sessão...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to={fallbackPathForRole(user.role)} replace />;
  }

  return <>{children}</>;
}

import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="p-8 text-center text-slate-600">Carregando sessão...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user.must_change_password && !location.pathname.startsWith("/change-password")) {
    return <Navigate to="/change-password" replace />;
  }

  return <>{children}</>;
}

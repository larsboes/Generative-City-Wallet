import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Skeleton } from "@/components/ui/skeleton";

type Role = "customer" | "business" | "admin";

export const RequireAuth = ({ children, role }: { children: JSX.Element; role?: Role }) => {
  const { user, role: userRole, loading } = useAuth();
  if (loading) {
    return <div className="grid min-h-screen place-items-center"><Skeleton className="h-8 w-32" /></div>;
  }
  if (!user) return <Navigate to="/auth" replace />;
  if (role && userRole !== role) {
    if (userRole === "business") return <Navigate to="/dashboard" replace />;
    return <Navigate to="/wallet" replace />;
  }
  return children;
};

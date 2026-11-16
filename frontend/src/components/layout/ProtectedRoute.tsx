import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status" aria-label="Loading">
        <Loader2 className="animate-spin text-accent" size={28} />
      </div>
    );
  }
  if (!isAuthenticated) {
    const back = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${back}`} replace />;
  }
  return <>{children}</>;
}

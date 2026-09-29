import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useUser } from '@/context/UserContext';
import { cumpleRequisitoAcceso, type RequisitoAcceso } from '@/routes/permissions';
import { LoadingState } from '@/components/ui/LoadingState';

interface PrivateRouteProps extends RequisitoAcceso {
  children: ReactNode;
}

/**
 * Protege una página: exige sesión y, si se indica, un permiso o rol
 * puntual. Usa siempre `cumpleRequisitoAcceso` para no duplicar la lógica.
 */
export function PrivateRoute({ children, permissionCode, roles }: PrivateRouteProps) {
  const { isAuthenticated } = useAuth();
  const { usuario, isLoading } = useUser();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (isLoading) {
    return <LoadingState label="Verificando permisos..." />;
  }

  if (!cumpleRequisitoAcceso(usuario, { permissionCode, roles })) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

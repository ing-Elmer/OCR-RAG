import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useMe } from '@/hooks/useMe';
import { cumpleRequisitoAcceso } from '@/routes/permissions';
import type { Usuario } from '@/types/usuario';

interface UserContextValue {
  usuario: Usuario | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
  /**
   * Solo sirve para decidir qué mostrar en la UI (ocultar botones, rutas,
   * etc.). El backend siempre revalida el permiso real; nunca usar esto para
   * proteger datos sensibles.
   */
  hasPermission: (permissionCode: string) => boolean;
  hasRole: (role: string) => boolean;
}

const UserContext = createContext<UserContextValue | null>(null);

/** Perfil, roles y permisos del usuario autenticado, resueltos desde `/api/me`. */
export function UserProvider({ children }: { children: ReactNode }) {
  const { data: usuario, isLoading, error, reload } = useMe();

  const value = useMemo<UserContextValue>(
    () => ({
      usuario,
      isLoading,
      error,
      reload,
      hasPermission: (permissionCode: string) => cumpleRequisitoAcceso(usuario, { permissionCode }),
      hasRole: (role: string) => cumpleRequisitoAcceso(usuario, { roles: [role] }),
    }),
    [usuario, isLoading, error, reload],
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser debe usarse dentro de un UserProvider.');
  }
  return context;
}

import { useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useAsyncResource, type AsyncResourceState } from '@/hooks/useAsyncResource';
import { obtenerPerfil } from '@/services/MeService';
import type { Usuario } from '@/types/usuario';

/**
 * Trae el perfil del usuario autenticado (`GET /api/me`). Si todavía no hay
 * sesión no llama a la API: devuelve `data: null` directamente.
 */
export function useMe(): AsyncResourceState<Usuario | null> {
  const { isAuthenticated } = useAuth();

  const loader = useCallback((): Promise<Usuario | null> => {
    if (!isAuthenticated) {
      return Promise.resolve(null);
    }
    return obtenerPerfil();
  }, [isAuthenticated]);

  return useAsyncResource(loader);
}

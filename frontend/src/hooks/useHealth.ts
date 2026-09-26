import { useCallback } from 'react';
import { useAsyncResource, type AsyncResourceState } from '@/hooks/useAsyncResource';
import { obtenerEstadoSalud, type EstadoSalud } from '@/services/HealthService';

/** Estado de salud de la API (`GET /health`). */
export function useHealth(): AsyncResourceState<EstadoSalud> {
  const loader = useCallback(() => obtenerEstadoSalud(), []);
  return useAsyncResource(loader);
}

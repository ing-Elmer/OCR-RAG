import { publicApi } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { request } from '@/services/ApiClient';

/** Estado de salud de la API y su base de datos. */
export interface EstadoSalud {
  status: string;
  database: string;
  version: string;
}

/** Consulta el health check de la API. Es un endpoint anónimo. */
export async function obtenerEstadoSalud(): Promise<EstadoSalud> {
  return request<EstadoSalud>(publicApi, { method: 'GET', url: endpoints.health.check });
}

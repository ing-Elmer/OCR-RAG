import { api } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { request } from '@/services/ApiClient';
import type { PayloadConsulta, ResultadoConsulta } from '@/types/consulta';

/** Ejecuta una consulta en lenguaje natural sobre el corpus procesado (`POST /api/consultas`). */
export async function realizarConsulta(payload: PayloadConsulta): Promise<ResultadoConsulta> {
  return request<ResultadoConsulta>(api, {
    method: 'POST',
    url: endpoints.consultas.crear,
    data: payload,
  });
}

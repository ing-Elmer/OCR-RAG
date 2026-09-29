import { api } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { request } from '@/services/ApiClient';
import type { Usuario } from '@/types/usuario';

/** Trae el perfil del usuario autenticado. */
export async function obtenerPerfil(): Promise<Usuario> {
  return request<Usuario>(api, { method: 'GET', url: endpoints.me.get });
}

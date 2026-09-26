import { publicApi } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { request, requestSinDatos } from '@/services/ApiClient';
import type { TokenPair } from '@/api/tokenStore';

export interface CredencialesLogin {
  username: string;
  password: string;
}

/** Inicia sesión contra `POST /api/auth/login` y devuelve el par de tokens. */
export async function iniciarSesion(credenciales: CredencialesLogin): Promise<TokenPair> {
  return request<TokenPair>(publicApi, {
    method: 'POST',
    url: endpoints.auth.login,
    data: credenciales,
  });
}

/**
 * Revoca el refresh token en el backend (`POST /api/auth/logout`).
 * El endpoint es idempotente: un token desconocido o ya revocado también responde 200.
 */
export async function cerrarSesion(refreshToken: string): Promise<void> {
  await requestSinDatos(publicApi, {
    method: 'POST',
    url: endpoints.auth.logout,
    data: { refreshToken },
  });
}

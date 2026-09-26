import axios, { isAxiosError, type InternalAxiosRequestConfig } from 'axios';
import { endpoints } from '@/api/endpoints';
import { tokenStore } from '@/api/tokenStore';
import type { ApiEnvelope } from '@/types/api';

const baseURL: string = import.meta.env.VITE_API_URL;

/** Cliente sin autenticación: health check, login, refresh. */
export const publicApi = axios.create({ baseURL });

/** Cliente autenticado: agrega el access token y renueva la sesión ante un 401. */
export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const accessToken = tokenStore.getAccessToken();
  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`);
  }
  return config;
});

interface RetriableRequestConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

interface RefreshResponseData {
  accessToken: string;
  refreshToken: string;
}

/** Se avisa cuando el refresh falla, para que la app cierre la sesión. */
type SessionExpiredHandler = () => void;
let onSessionExpired: SessionExpiredHandler | null = null;

export function setSessionExpiredHandler(handler: SessionExpiredHandler | null): void {
  onSessionExpired = handler;
}

/**
 * Promesa compartida de renovación: si llegan varios 401 concurrentes, todos
 * esperan la misma llamada a `/api/auth/refresh` en lugar de disparar una por
 * cada request. Se limpia apenas termina (con éxito o error).
 */
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) {
    throw new Error('No hay una sesión activa para renovar.');
  }

  const response = await publicApi.post<ApiEnvelope<RefreshResponseData>>(endpoints.auth.refresh, {
    refreshToken,
  });

  const data = response.data.data;
  if (!data) {
    throw new Error('La renovación de sesión no devolvió tokens.');
  }

  tokenStore.setTokens(data);
  return data.accessToken;
}

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!isAxiosError(error)) {
      return Promise.reject(error);
    }

    const originalRequest = error.config as RetriableRequestConfig | undefined;
    const isUnauthorized = error.response?.status === 401;

    if (!isUnauthorized || !originalRequest || originalRequest._retried) {
      return Promise.reject(error);
    }

    originalRequest._retried = true;

    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const accessToken = await refreshPromise;
      originalRequest.headers.set('Authorization', `Bearer ${accessToken}`);
      return await api.request(originalRequest);
    } catch (refreshError) {
      tokenStore.clear();
      onSessionExpired?.();
      return Promise.reject(refreshError);
    }
  },
);

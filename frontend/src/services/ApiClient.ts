import { isAxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type { ApiEnvelope, ApiFieldErrors, ApiStatus } from '@/types/api';

/**
 * Error de la API: conserva el mensaje del backend y, si los hay, los
 * errores de validación por campo (`{ campo: ["mensaje"] }`).
 */
export class ApiError extends Error {
  readonly status: ApiStatus;
  readonly errors: ApiFieldErrors | null;
  readonly httpStatus: number | null;

  constructor(message: string, status: ApiStatus, errors: ApiFieldErrors | null, httpStatus: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.errors = errors;
    this.httpStatus = httpStatus;
  }
}

const MENSAJE_SIN_CONEXION = 'No se pudo conectar con el servidor. Intentá de nuevo en unos minutos.';
const MENSAJE_SIN_DATOS = 'La respuesta del servidor no incluyó datos.';

/**
 * Ejecuta la request y devuelve el envelope ya validado (status distinto de
 * `Error`). Centraliza la traducción de errores de red y HTTP a `ApiError`.
 */
async function enviar<T, M = unknown>(client: AxiosInstance, config: AxiosRequestConfig): Promise<ApiEnvelope<T, M>> {
  try {
    const response = await client.request<ApiEnvelope<T, M>>(config);
    const envelope = response.data;

    if (envelope.status === 'Error') {
      throw new ApiError(envelope.message, envelope.status, envelope.errors, response.status);
    }

    return envelope;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (isAxiosError(error) && error.response) {
      const envelope = error.response.data as Partial<ApiEnvelope<unknown>> | undefined;
      throw new ApiError(
        envelope?.message ?? MENSAJE_SIN_CONEXION,
        envelope?.status ?? 'Error',
        envelope?.errors ?? null,
        error.response.status,
      );
    }
    throw new ApiError(MENSAJE_SIN_CONEXION, 'Error', null);
  }
}

/**
 * Ejecuta una request con el cliente axios indicado y desenvuelve el
 * envelope estándar de la API. Nunca se usa axios directo fuera de acá.
 */
export async function request<T>(client: AxiosInstance, config: AxiosRequestConfig): Promise<T> {
  const envelope = await enviar<T>(client, config);
  if (envelope.data === null) {
    throw new ApiError(MENSAJE_SIN_DATOS, envelope.status, envelope.errors);
  }
  return envelope.data;
}

/**
 * Igual que `request<T>()`, para endpoints que responden sin `data`
 * (p. ej. `ApiResponse.success(...)` del backend, como el logout).
 */
export async function requestSinDatos(client: AxiosInstance, config: AxiosRequestConfig): Promise<void> {
  await enviar<null>(client, config);
}

/** Resultado de `requestConMeta<T, M>()`: datos más metadatos (p. ej. paginación). */
export interface ResultadoConMeta<T, M> {
  data: T;
  meta: M;
}

/**
 * Igual que `request<T>()`, pero además devuelve `meta` (p. ej. `{ total, limite, offset }`
 * de un listado paginado). Reutiliza el mismo manejo de errores de `enviar()`.
 */
export async function requestConMeta<T, M>(
  client: AxiosInstance,
  config: AxiosRequestConfig,
): Promise<ResultadoConMeta<T, M>> {
  const envelope = await enviar<T, M>(client, config);
  if (envelope.data === null) {
    throw new ApiError(MENSAJE_SIN_DATOS, envelope.status, envelope.errors);
  }
  if (envelope.meta === null) {
    throw new ApiError(MENSAJE_SIN_DATOS, envelope.status, envelope.errors);
  }
  return { data: envelope.data, meta: envelope.meta };
}

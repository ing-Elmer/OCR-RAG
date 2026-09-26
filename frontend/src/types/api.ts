/**
 * Tipos del envelope estándar que devuelve toda la API.
 * Ver contrato en CLAUDE.md del proyecto.
 */

/** Estado del envelope devuelto por el backend. */
export type ApiStatus = 'Success' | 'Created' | 'Error';

/** Errores de validación por campo: `{ "campo": ["mensaje"] }`. */
export type ApiFieldErrors = Record<string, string[]>;

/**
 * Envelope estándar que envuelve toda respuesta de la API.
 * `M` es el tipo de `meta` (p. ej. datos de paginación); por defecto `unknown`
 * para los endpoints que no lo tipan explícitamente.
 */
export interface ApiEnvelope<T, M = unknown> {
  status: ApiStatus;
  message: string;
  data: T | null;
  errors: ApiFieldErrors | null;
  meta: M | null;
}

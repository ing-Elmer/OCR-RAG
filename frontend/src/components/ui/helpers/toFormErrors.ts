import { ApiError } from '@/services/ApiClient';
import type { ApiFieldErrors } from '@/types/api';

/** Mapa simple `{ campo: "mensaje" }`, listo para mostrar junto a cada input. */
export type FormErrors = Record<string, string>;

/**
 * Convierte los errores de campo del backend (`{ campo: ["mensaje"] }`) al
 * formato que consumen los formularios. Si el error no es un `ApiError` o no
 * trae errores de campo, devuelve un objeto vacío (el mensaje general se
 * muestra aparte, con `error.message`).
 */
export function toFormErrors(error: unknown): FormErrors {
  if (!(error instanceof ApiError) || !error.errors) {
    return {};
  }
  return aplanarPrimerMensaje(error.errors);
}

function aplanarPrimerMensaje(errores: ApiFieldErrors): FormErrors {
  const resultado: FormErrors = {};
  for (const [campo, mensajes] of Object.entries(errores)) {
    const [primerMensaje] = mensajes;
    if (primerMensaje) {
      resultado[campo] = primerMensaje;
    }
  }
  return resultado;
}

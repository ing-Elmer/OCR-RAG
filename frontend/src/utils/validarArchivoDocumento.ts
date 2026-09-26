/**
 * Validación de archivo en el cliente, solo como ayuda de UX: el backend
 * siempre revalida tipo y tamaño en `POST /api/documentos`.
 */

const TIPOS_ACEPTADOS: readonly string[] = ['application/pdf', 'image/png', 'image/jpeg', 'image/tiff'];
const TAMANO_MAXIMO_BYTES = 20 * 1024 * 1024;

export interface ResultadoValidacionArchivo {
  esValido: boolean;
  mensaje: string | null;
}

/** Valida que el archivo tenga un tipo aceptado (PDF, PNG, JPG/JPEG, TIFF) y no supere los 20 MB. */
export function validarArchivoDocumento(archivo: File): ResultadoValidacionArchivo {
  if (!TIPOS_ACEPTADOS.includes(archivo.type)) {
    return { esValido: false, mensaje: 'El archivo debe ser PDF, PNG, JPG o TIFF.' };
  }
  if (archivo.size > TAMANO_MAXIMO_BYTES) {
    return { esValido: false, mensaje: 'El archivo no puede superar los 20 MB.' };
  }
  return { esValido: true, mensaje: null };
}

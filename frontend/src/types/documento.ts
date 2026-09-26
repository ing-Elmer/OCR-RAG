/** Estado de procesamiento de un documento cargado para OCR + RAG. */
export type EstadoDocumento = 'pendiente' | 'procesando' | 'procesado' | 'error';

/** Documento tal como lo devuelve la API (`GET /api/documentos`, `POST /api/documentos`). */
export interface Documento {
  id: number;
  nombreArchivo: string;
  /** URL de origen si vino de la carga masiva de corpus; `null` si se subió a mano. */
  fuenteUrl: string | null;
  tipoContenido: string;
  tamanoBytes: number;
  estado: EstadoDocumento;
  idioma: string | null;
  paginas: number | null;
  cantidadChunks: number;
  errorDetalle: string | null;
  createdAt: string;
}

/** Metadatos de paginación de `GET /api/documentos`. */
export interface MetaListaDocumentos {
  total: number;
  limite: number;
  offset: number;
}

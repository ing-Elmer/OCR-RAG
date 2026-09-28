import type { TipoDocumento } from '@/types/documento';

/** Fragmento de un documento citado en la respuesta de una consulta. */
export interface FuenteConsulta {
  documentoId: number;
  nombreArchivo: string;
  /** URL de origen si el documento vino de la carga masiva de corpus; `null` si se subió a mano. */
  fuenteUrl: string | null;
  /** Posición del fragmento dentro de su documento (no es el número de cita). */
  orden: number;
  pagina: number | null;
  /** Nombre de la norma citada, si el documento es una; `null` si no aplica. */
  norma: string | null;
  /** Artículo de la norma citado, si aplica; `null` si no. */
  articulo: string | null;
  fragmento: string;
  similitud: number;
  tipoDocumento: TipoDocumento;
}

/** Resultado de `POST /api/consultas`. */
export interface ResultadoConsulta {
  respuesta: string;
  fuentes: FuenteConsulta[];
}

/** Cuerpo enviado a `POST /api/consultas`. */
export interface PayloadConsulta {
  pregunta: string;
  documentoIds?: number[];
  /** Filtra el corpus a estas categorías; sin indicar, se consulta sobre todos los tipos. */
  tiposDocumento?: TipoDocumento[];
  topK?: number;
}

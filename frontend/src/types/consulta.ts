/** Fragmento de un documento citado en la respuesta de una consulta. */
export interface FuenteConsulta {
  documentoId: number;
  nombreArchivo: string;
  /** URL de origen si el documento vino de la carga masiva de corpus; `null` si se subió a mano. */
  fuenteUrl: string | null;
  /** Posición del fragmento dentro de su documento (no es el número de cita). */
  orden: number;
  pagina: number | null;
  fragmento: string;
  similitud: number;
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
  topK?: number;
}

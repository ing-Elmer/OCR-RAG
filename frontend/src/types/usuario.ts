/** Perfil del usuario autenticado, tal como lo devuelve `GET /api/me`. */
export interface Usuario {
  /** `bigint` en PostgreSQL (`ocr_rag.ocr_usuario.id`), serializado como número en el JSON. */
  id: number;
  username: string;
  nombreCompleto: string;
  roles: string[];
  permisos: string[];
}

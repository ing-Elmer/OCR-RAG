import { api } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { request, requestConMeta } from '@/services/ApiClient';
import type { Documento, MetaListaDocumentos, TipoDocumento } from '@/types/documento';

export interface DatosCargaDocumento {
  archivo: File;
  /** Idioma para el OCR (p. ej. `spa+eng`); si no se indica, lo resuelve el backend. */
  idioma?: string;
  /** Categoría del documento; si no se indica, el backend la clasifica con IA al procesar. */
  tipoDocumento?: TipoDocumento;
}

export interface ListaDocumentos {
  documentos: Documento[];
  meta: MetaListaDocumentos;
}

/** Campos editables de un documento (`PATCH /api/documentos/{id}`); solo se envían los que cambiaron. */
export interface DatosActualizarDocumento {
  tipoDocumento?: TipoDocumento;
  /** Omitido = no cambiar; `null` = quitar la norma; texto = reemplazarla (1..100 caracteres). */
  norma?: string | null;
}

/** Sube un documento (PDF o imagen) para procesar con OCR (`POST /api/documentos`, multipart/form-data). */
export async function cargarDocumento({ archivo, idioma, tipoDocumento }: DatosCargaDocumento): Promise<Documento> {
  const formData = new FormData();
  formData.append('archivo', archivo);
  if (idioma) {
    formData.append('idioma', idioma);
  }
  if (tipoDocumento) {
    formData.append('tipoDocumento', tipoDocumento);
  }

  return request<Documento>(api, {
    method: 'POST',
    url: endpoints.documentos.crear,
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/** Actualiza el tipo y/o la norma de un documento (`PATCH /api/documentos/{id}`). */
export async function actualizarDocumento(id: number, datos: DatosActualizarDocumento): Promise<Documento> {
  return request<Documento>(api, {
    method: 'PATCH',
    url: endpoints.documentos.actualizar(id),
    data: datos,
  });
}

/** Lista documentos paginados (`GET /api/documentos`). */
export async function listarDocumentos(limite: number, offset: number): Promise<ListaDocumentos> {
  const { data, meta } = await requestConMeta<Documento[], MetaListaDocumentos>(api, {
    method: 'GET',
    url: endpoints.documentos.listar,
    params: { limite, offset },
  });
  return { documentos: data, meta };
}

/** Trae un documento puntual (`GET /api/documentos/{id}`). */
export async function obtenerDocumento(id: number): Promise<Documento> {
  return request<Documento>(api, { method: 'GET', url: endpoints.documentos.obtener(id) });
}

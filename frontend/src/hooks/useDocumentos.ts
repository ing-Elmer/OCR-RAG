import { useCallback, useEffect, useState } from 'react';
import { useAsyncResource, type AsyncResourceState } from '@/hooks/useAsyncResource';
import { listarDocumentos, type ListaDocumentos } from '@/services/DocumentoService';
import type { EstadoDocumento } from '@/types/documento';

const TAMANIO_PAGINA = 20;
const INTERVALO_POLLING_MS = 3000;
const ESTADOS_EN_PROCESO: ReadonlySet<EstadoDocumento> = new Set(['pendiente', 'procesando']);

export interface UseDocumentosResult extends AsyncResourceState<ListaDocumentos> {
  limite: number;
  offset: number;
  puedeIrAnterior: boolean;
  puedeIrSiguiente: boolean;
  irAPaginaAnterior: () => void;
  irAPaginaSiguiente: () => void;
}

/**
 * Lista documentos paginados (`GET /api/documentos`) y hace polling cada
 * ~3 s mientras haya alguno `pendiente` o `procesando` en la página actual.
 * El polling se detiene solo cuando ya no hay documentos en proceso o al
 * desmontar el componente que usa el hook.
 */
export function useDocumentos(): UseDocumentosResult {
  const [offset, setOffset] = useState(0);

  const loader = useCallback(() => listarDocumentos(TAMANIO_PAGINA, offset), [offset]);
  const recurso = useAsyncResource(loader);
  const { data, reload } = recurso;

  const hayDocumentosEnProceso = data
    ? data.documentos.some((documento) => ESTADOS_EN_PROCESO.has(documento.estado))
    : false;

  useEffect(() => {
    if (!hayDocumentosEnProceso) {
      return;
    }

    const intervalId = window.setInterval(() => {
      reload();
    }, INTERVALO_POLLING_MS);

    return () => window.clearInterval(intervalId);
  }, [hayDocumentosEnProceso, reload]);

  const irAPaginaAnterior = useCallback(() => {
    setOffset((actual) => Math.max(0, actual - TAMANIO_PAGINA));
  }, []);

  const irAPaginaSiguiente = useCallback(() => {
    setOffset((actual) => actual + TAMANIO_PAGINA);
  }, []);

  return {
    ...recurso,
    limite: TAMANIO_PAGINA,
    offset,
    puedeIrAnterior: offset > 0,
    puedeIrSiguiente: data ? offset + TAMANIO_PAGINA < data.meta.total : false,
    irAPaginaAnterior,
    irAPaginaSiguiente,
  };
}

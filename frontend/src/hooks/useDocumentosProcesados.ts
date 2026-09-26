import { useCallback } from 'react';
import { useAsyncResource, type AsyncResourceState } from '@/hooks/useAsyncResource';
import { listarDocumentos } from '@/services/DocumentoService';
import type { Documento } from '@/types/documento';

const LIMITE_DOCUMENTOS = 100;

/**
 * Documentos ya procesados, para el filtro opcional de la pantalla de
 * Consultas. Si `habilitado` es `false` (el usuario no tiene `DOCUMENTOS_VER`)
 * no llama a la API: el filtro se oculta directamente.
 */
export function useDocumentosProcesados(habilitado: boolean): AsyncResourceState<Documento[]> {
  const loader = useCallback(async (): Promise<Documento[]> => {
    if (!habilitado) {
      return [];
    }
    const { documentos } = await listarDocumentos(LIMITE_DOCUMENTOS, 0);
    return documentos.filter((documento) => documento.estado === 'procesado');
  }, [habilitado]);

  return useAsyncResource(loader);
}

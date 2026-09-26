import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDocumentos } from '@/hooks/useDocumentos';
import * as DocumentoService from '@/services/DocumentoService';
import type { Documento } from '@/types/documento';

function crearDocumento(overrides: Partial<Documento> = {}): Documento {
  return {
    id: 1,
    nombreArchivo: 'archivo.pdf',
    fuenteUrl: null,
    tipoContenido: 'application/pdf',
    tamanoBytes: 1024,
    estado: 'pendiente',
    idioma: 'spa',
    paginas: null,
    cantidadChunks: 0,
    errorDetalle: null,
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('useDocumentos', () => {
  beforeEach(() => {
    // `shouldAdvanceTime` deja que el reloj falso también avance con el
    // tiempo real: sin esto, `waitFor` (que usa `setTimeout` por dentro)
    // queda esperando para siempre bajo fake timers.
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('hace polling mientras haya documentos pendientes o en proceso, se detiene cuando terminan y al desmontar', async () => {
    const listarDocumentosMock = vi
      .spyOn(DocumentoService, 'listarDocumentos')
      .mockResolvedValueOnce({
        documentos: [crearDocumento({ estado: 'pendiente' })],
        meta: { total: 1, limite: 20, offset: 0 },
      })
      .mockResolvedValueOnce({
        documentos: [crearDocumento({ estado: 'procesado', paginas: 3, cantidadChunks: 5 })],
        meta: { total: 1, limite: 20, offset: 0 },
      });

    const { result, unmount } = renderHook(() => useDocumentos());

    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(listarDocumentosMock).toHaveBeenCalledTimes(1);

    // Todavía hay un documento "pendiente": a los 3s dispara un nuevo pedido.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(listarDocumentosMock).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(result.current.data?.documentos[0]?.estado).toBe('procesado'));

    // Ya no hay documentos en proceso: no debe disparar más pedidos.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(listarDocumentosMock).toHaveBeenCalledTimes(2);

    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(listarDocumentosMock).toHaveBeenCalledTimes(2);
  });

  it('no hace polling cuando la página cargada no tiene documentos pendientes ni en proceso', async () => {
    const listarDocumentosMock = vi.spyOn(DocumentoService, 'listarDocumentos').mockResolvedValue({
      documentos: [crearDocumento({ estado: 'procesado' })],
      meta: { total: 1, limite: 20, offset: 0 },
    });

    const { result } = renderHook(() => useDocumentos());

    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(listarDocumentosMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(listarDocumentosMock).toHaveBeenCalledTimes(1);
  });
});

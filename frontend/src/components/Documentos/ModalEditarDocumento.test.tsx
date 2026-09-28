import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ModalEditarDocumento } from '@/components/Documentos/ModalEditarDocumento';
import { ApiError } from '@/services/ApiClient';
import * as DocumentoService from '@/services/DocumentoService';
import type { Documento } from '@/types/documento';

function crearDocumento(overrides: Partial<Documento> = {}): Documento {
  return {
    id: 1,
    nombreArchivo: 'manifiesto.pdf',
    fuenteUrl: null,
    tipoContenido: 'application/pdf',
    tamanoBytes: 1024,
    estado: 'procesado',
    idioma: 'spa',
    paginas: 3,
    cantidadChunks: 5,
    errorDetalle: null,
    tipoDocumento: 'otro',
    norma: null,
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('ModalEditarDocumento', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('envía por PATCH solo los campos que cambiaron', async () => {
    const usuario = userEvent.setup();
    const documento = crearDocumento();
    const actualizarDocumentoMock = vi.spyOn(DocumentoService, 'actualizarDocumento').mockResolvedValue(
      crearDocumento({ norma: 'CAUCA' }),
    );
    const onGuardado = vi.fn();

    render(<ModalEditarDocumento documento={documento} isOpen onClose={vi.fn()} onGuardado={onGuardado} />);

    await usuario.type(screen.getByLabelText('Norma'), 'CAUCA');
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(onGuardado).toHaveBeenCalledTimes(1));
    expect(actualizarDocumentoMock).toHaveBeenCalledWith(1, { norma: 'CAUCA' });
  });

  it('envía el tipoDocumento solo cuando cambia, sin tocar la norma', async () => {
    const usuario = userEvent.setup();
    const documento = crearDocumento({ norma: 'CAUCA' });
    const actualizarDocumentoMock = vi.spyOn(DocumentoService, 'actualizarDocumento').mockResolvedValue(
      crearDocumento({ tipoDocumento: 'normativa', norma: 'CAUCA' }),
    );

    render(<ModalEditarDocumento documento={documento} isOpen onClose={vi.fn()} onGuardado={vi.fn()} />);

    await usuario.selectOptions(screen.getByLabelText('Tipo de documento'), 'normativa');
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(actualizarDocumentoMock).toHaveBeenCalledWith(1, { tipoDocumento: 'normativa' }));
  });

  it('envía norma null al vaciar el campo, para quitar la norma', async () => {
    // El backend rechaza la norma vacía (1..100 caracteres): quitarla se expresa con `null`.
    const usuario = userEvent.setup();
    const documento = crearDocumento({ norma: 'CAUCA' });
    const actualizarDocumentoMock = vi.spyOn(DocumentoService, 'actualizarDocumento').mockResolvedValue(
      crearDocumento({ norma: null }),
    );

    render(<ModalEditarDocumento documento={documento} isOpen onClose={vi.fn()} onGuardado={vi.fn()} />);

    await usuario.clear(screen.getByLabelText('Norma'));
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(actualizarDocumentoMock).toHaveBeenCalledWith(1, { norma: null }));
  });

  it('muestra los errores del backend junto al campo y no cierra el modal', async () => {
    const usuario = userEvent.setup();
    const documento = crearDocumento();
    vi.spyOn(DocumentoService, 'actualizarDocumento').mockRejectedValue(
      new ApiError('Datos inválidos.', 'Error', { norma: ['La norma debe tener entre 1 y 100 caracteres.'] }, 400),
    );
    const onGuardado = vi.fn();

    render(<ModalEditarDocumento documento={documento} isOpen onClose={vi.fn()} onGuardado={onGuardado} />);

    await usuario.type(screen.getByLabelText('Norma'), 'X'.repeat(101));
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByText('La norma debe tener entre 1 y 100 caracteres.')).toBeInTheDocument();
    expect(onGuardado).not.toHaveBeenCalled();
  });

  it('deshabilita el envío mientras la actualización está en curso', async () => {
    const usuario = userEvent.setup();
    const documento = crearDocumento();
    let resolverPromesa: (documento: Documento) => void = () => {};
    vi.spyOn(DocumentoService, 'actualizarDocumento').mockReturnValue(
      new Promise((resolve) => {
        resolverPromesa = resolve;
      }),
    );

    render(<ModalEditarDocumento documento={documento} isOpen onClose={vi.fn()} onGuardado={vi.fn()} />);

    await usuario.type(screen.getByLabelText('Norma'), 'CAUCA');
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(screen.getByRole('button', { name: 'Procesando...' })).toBeDisabled();

    resolverPromesa(crearDocumento({ norma: 'CAUCA' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Procesando...' })).not.toBeInTheDocument());
  });
});

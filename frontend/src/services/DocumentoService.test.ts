import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { api } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { actualizarDocumento, cargarDocumento, listarDocumentos, obtenerDocumento } from '@/services/DocumentoService';
import type { Documento } from '@/types/documento';

function crearDocumento(overrides: Partial<Documento> = {}): Documento {
  return {
    id: 1,
    nombreArchivo: 'archivo.pdf',
    fuenteUrl: null,
    tipoContenido: 'application/pdf',
    tamanoBytes: 2048,
    estado: 'pendiente',
    idioma: 'spa+eng',
    paginas: null,
    cantidadChunks: 0,
    errorDetalle: null,
    tipoDocumento: 'otro',
    norma: null,
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('DocumentoService', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(api);
  });

  afterEach(() => {
    mock.restore();
  });

  it('cargarDocumento envía el archivo y el idioma como multipart/form-data', async () => {
    const documento = crearDocumento();
    mock.onPost(endpoints.documentos.crear).reply(201, { status: 'Created', message: 'ok', data: documento, errors: null, meta: null });

    const archivo = new File(['contenido'], 'archivo.pdf', { type: 'application/pdf' });
    const resultado = await cargarDocumento({ archivo, idioma: 'spa+eng' });

    expect(resultado).toEqual(documento);

    const peticion = mock.history.post[0];
    expect(peticion.headers?.['Content-Type']).toBe('multipart/form-data');
    const formData = peticion.data as FormData;
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get('archivo')).toBe(archivo);
    expect(formData.get('idioma')).toBe('spa+eng');
  });

  it('cargarDocumento no agrega el campo idioma cuando no se indica', async () => {
    const documento = crearDocumento();
    mock.onPost(endpoints.documentos.crear).reply(201, { status: 'Created', message: 'ok', data: documento, errors: null, meta: null });

    const archivo = new File(['contenido'], 'archivo.pdf', { type: 'application/pdf' });
    await cargarDocumento({ archivo });

    const formData = mock.history.post[0].data as FormData;
    expect(formData.has('idioma')).toBe(false);
  });

  it('cargarDocumento envía el tipoDocumento cuando se lo indica explícitamente', async () => {
    const documento = crearDocumento({ tipoDocumento: 'normativa' });
    mock.onPost(endpoints.documentos.crear).reply(201, { status: 'Created', message: 'ok', data: documento, errors: null, meta: null });

    const archivo = new File(['contenido'], 'norma.pdf', { type: 'application/pdf' });
    await cargarDocumento({ archivo, tipoDocumento: 'normativa' });

    const formData = mock.history.post[0].data as FormData;
    expect(formData.get('tipoDocumento')).toBe('normativa');
  });

  it('cargarDocumento no agrega el campo tipoDocumento en modo de detección automática', async () => {
    const documento = crearDocumento();
    mock.onPost(endpoints.documentos.crear).reply(201, { status: 'Created', message: 'ok', data: documento, errors: null, meta: null });

    const archivo = new File(['contenido'], 'archivo.pdf', { type: 'application/pdf' });
    await cargarDocumento({ archivo });

    const formData = mock.history.post[0].data as FormData;
    expect(formData.has('tipoDocumento')).toBe(false);
  });

  it('listarDocumentos pide limite y offset como parámetros y devuelve data + meta', async () => {
    const documentos = [crearDocumento()];
    mock.onGet(endpoints.documentos.listar).reply(200, {
      status: 'Success',
      message: 'ok',
      data: documentos,
      errors: null,
      meta: { total: 1, limite: 20, offset: 0 },
    });

    const resultado = await listarDocumentos(20, 0);

    expect(resultado.documentos).toEqual(documentos);
    expect(resultado.meta).toEqual({ total: 1, limite: 20, offset: 0 });
    expect(mock.history.get[0].params).toEqual({ limite: 20, offset: 0 });
  });

  it('obtenerDocumento pide el documento por id', async () => {
    const documento = crearDocumento({ id: 42 });
    mock.onGet(endpoints.documentos.obtener(42)).reply(200, { status: 'Success', message: 'ok', data: documento, errors: null, meta: null });

    const resultado = await obtenerDocumento(42);

    expect(resultado).toEqual(documento);
  });

  it('actualizarDocumento envía por PATCH solo los campos indicados', async () => {
    const documento = crearDocumento({ id: 7, tipoDocumento: 'normativa', norma: 'CAUCA' });
    mock.onPatch(endpoints.documentos.actualizar(7)).reply(200, { status: 'Success', message: 'ok', data: documento, errors: null, meta: null });

    const resultado = await actualizarDocumento(7, { norma: 'CAUCA' });

    expect(resultado).toEqual(documento);
    expect(JSON.parse(mock.history.patch[0].data as string)).toEqual({ norma: 'CAUCA' });
  });

  it('actualizarDocumento propaga los errores de validación del backend', async () => {
    mock.onPatch(endpoints.documentos.actualizar(7)).reply(400, {
      status: 'Error',
      message: 'Datos inválidos.',
      data: null,
      errors: { norma: ['La norma debe tener entre 1 y 100 caracteres.'] },
      meta: null,
    });

    await expect(actualizarDocumento(7, { norma: '' })).rejects.toMatchObject({
      errors: { norma: ['La norma debe tener entre 1 y 100 caracteres.'] },
    });
  });
});

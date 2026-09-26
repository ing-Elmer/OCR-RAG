import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { publicApi } from '@/api/api';
import { ApiError, requestConMeta } from '@/services/ApiClient';
import type { ApiEnvelope } from '@/types/api';

interface MetaPrueba {
  total: number;
}

describe('requestConMeta', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(publicApi);
  });

  afterEach(() => {
    mock.restore();
  });

  it('devuelve data y meta cuando la respuesta es exitosa', async () => {
    const envelope: ApiEnvelope<string[], MetaPrueba> = {
      status: 'Success',
      message: 'ok',
      data: ['a', 'b'],
      errors: null,
      meta: { total: 2 },
    };
    mock.onGet('/recurso').reply(200, envelope);

    const resultado = await requestConMeta<string[], MetaPrueba>(publicApi, { method: 'GET', url: '/recurso' });

    expect(resultado.data).toEqual(['a', 'b']);
    expect(resultado.meta).toEqual({ total: 2 });
  });

  it('lanza un ApiError si el envelope no trae meta', async () => {
    const envelope: ApiEnvelope<string[], MetaPrueba> = {
      status: 'Success',
      message: 'ok',
      data: ['a'],
      errors: null,
      meta: null,
    };
    mock.onGet('/recurso-sin-meta').reply(200, envelope);

    await expect(
      requestConMeta<string[], MetaPrueba>(publicApi, { method: 'GET', url: '/recurso-sin-meta' }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it('propaga un ApiError con los errores de campo cuando el backend responde un error', async () => {
    mock.onGet('/recurso-error').reply(400, {
      status: 'Error',
      message: 'Solicitud inválida',
      data: null,
      errors: { campo: ['mensaje'] },
      meta: null,
    });

    await expect(
      requestConMeta<string[], MetaPrueba>(publicApi, { method: 'GET', url: '/recurso-error' }),
    ).rejects.toMatchObject({ message: 'Solicitud inválida', errors: { campo: ['mensaje'] } });
  });
});

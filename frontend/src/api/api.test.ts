import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { api, publicApi } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { tokenStore } from '@/api/tokenStore';
import type { ApiEnvelope } from '@/types/api';

function envelopeExito<T>(data: T): ApiEnvelope<T> {
  return { status: 'Success', message: 'ok', data, errors: null, meta: null };
}

function envelopeError(mensaje: string): ApiEnvelope<null> {
  return { status: 'Error', message: mensaje, data: null, errors: null, meta: null };
}

describe('interceptor de refresh de api', () => {
  let apiMock: MockAdapter;
  let publicMock: MockAdapter;

  beforeEach(() => {
    apiMock = new MockAdapter(api);
    publicMock = new MockAdapter(publicApi);
    tokenStore.setTokens({ accessToken: 'token-vencido', refreshToken: 'refresh-valido' });
  });

  afterEach(() => {
    apiMock.restore();
    publicMock.restore();
    tokenStore.clear();
  });

  it('ante varios 401 concurrentes dispara un solo refresh y reintenta cada request original', async () => {
    apiMock.onGet('/recurso-a').reply(() => {
      const tokenActual = tokenStore.getAccessToken();
      return tokenActual === 'token-nuevo' ? [200, envelopeExito({ valor: 'a' })] : [401, envelopeError('Token vencido')];
    });
    apiMock.onGet('/recurso-b').reply(() => {
      const tokenActual = tokenStore.getAccessToken();
      return tokenActual === 'token-nuevo' ? [200, envelopeExito({ valor: 'b' })] : [401, envelopeError('Token vencido')];
    });

    let llamadasRefresh = 0;
    publicMock.onPost(endpoints.auth.refresh).reply(() => {
      llamadasRefresh += 1;
      return [200, envelopeExito({ accessToken: 'token-nuevo', refreshToken: 'refresh-nuevo' })];
    });

    const [respuestaA, respuestaB] = await Promise.all([api.get('/recurso-a'), api.get('/recurso-b')]);

    expect(llamadasRefresh).toBe(1);
    expect(respuestaA.status).toBe(200);
    expect(respuestaB.status).toBe(200);
    expect(tokenStore.getAccessToken()).toBe('token-nuevo');
    expect(tokenStore.getRefreshToken()).toBe('refresh-nuevo');
  });

  it('cierra la sesión (limpia los tokens) si el refresh falla', async () => {
    apiMock.onGet('/recurso-c').reply(401, envelopeError('Token vencido'));
    publicMock.onPost(endpoints.auth.refresh).reply(401, envelopeError('Refresh inválido'));

    await expect(api.get('/recurso-c')).rejects.toBeTruthy();

    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
  });

  it('no reintenta dos veces la misma request ante un segundo 401', async () => {
    let intentos = 0;
    apiMock.onGet('/recurso-d').reply(() => {
      intentos += 1;
      return [401, envelopeError('Token vencido')];
    });
    publicMock.onPost(endpoints.auth.refresh).reply(200, envelopeExito({ accessToken: 'token-nuevo', refreshToken: 'refresh-nuevo' }));

    await expect(api.get('/recurso-d')).rejects.toBeTruthy();

    expect(intentos).toBe(2);
  });
});

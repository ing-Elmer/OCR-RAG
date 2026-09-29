import { beforeEach, describe, expect, it } from 'vitest';
import { tokenStore } from '@/api/tokenStore';

describe('tokenStore', () => {
  beforeEach(() => {
    tokenStore.clear();
  });

  it('no tiene sesión cuando no se guardó ningún token', () => {
    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
    expect(tokenStore.hasSession()).toBe(false);
  });

  it('guarda y devuelve el par de tokens', () => {
    tokenStore.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });

    expect(tokenStore.getAccessToken()).toBe('access-1');
    expect(tokenStore.getRefreshToken()).toBe('refresh-1');
    expect(tokenStore.hasSession()).toBe(true);
  });

  it('sobrescribe los tokens al guardar un par nuevo', () => {
    tokenStore.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });
    tokenStore.setTokens({ accessToken: 'access-2', refreshToken: 'refresh-2' });

    expect(tokenStore.getAccessToken()).toBe('access-2');
    expect(tokenStore.getRefreshToken()).toBe('refresh-2');
  });

  it('limpia ambos tokens', () => {
    tokenStore.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });

    tokenStore.clear();

    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
    expect(tokenStore.hasSession()).toBe(false);
  });
});

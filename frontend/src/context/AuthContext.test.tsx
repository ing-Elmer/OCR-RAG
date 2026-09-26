import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { tokenStore } from '@/api/tokenStore';
import { cerrarSesion } from '@/services/AuthService';

vi.mock('@/services/AuthService', () => ({
  cerrarSesion: vi.fn(() => Promise.resolve()),
}));

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('AuthContext', () => {
  beforeEach(() => {
    tokenStore.clear();
    vi.mocked(cerrarSesion).mockClear();
  });

  it('arranca sin sesión cuando no hay tokens guardados', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(false);
  });

  it('arranca con sesión si ya había tokens guardados', () => {
    tokenStore.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(true);
  });

  it('login guarda los tokens y marca la sesión como autenticada', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login({ accessToken: 'access-1', refreshToken: 'refresh-1' });
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(tokenStore.getAccessToken()).toBe('access-1');
    expect(tokenStore.getRefreshToken()).toBe('refresh-1');
  });

  it('logout limpia los tokens y marca la sesión como no autenticada', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login({ accessToken: 'access-1', refreshToken: 'refresh-1' });
    });
    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
  });

  it('logout revoca el refresh token en el backend', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login({ accessToken: 'access-1', refreshToken: 'refresh-1' });
    });
    act(() => {
      result.current.logout();
    });

    expect(cerrarSesion).toHaveBeenCalledTimes(1);
    expect(cerrarSesion).toHaveBeenCalledWith('refresh-1');
  });

  it('logout cierra la sesión local aunque falle la revocación en el backend', async () => {
    vi.mocked(cerrarSesion).mockRejectedValueOnce(new Error('sin conexión'));
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login({ accessToken: 'access-1', refreshToken: 'refresh-1' });
    });
    await act(async () => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(tokenStore.getRefreshToken()).toBeNull();
  });

  it('logout sin sesión no llama al backend', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.logout();
    });

    expect(cerrarSesion).not.toHaveBeenCalled();
  });

  it('lanza un error si se usa fuera de un AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth debe usarse dentro de un AuthProvider.');
  });
});

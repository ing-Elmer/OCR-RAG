import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { setSessionExpiredHandler } from '@/api/api';
import { tokenStore, type TokenPair } from '@/api/tokenStore';
import { cerrarSesion } from '@/services/AuthService';

interface AuthContextValue {
  /** Hay tokens guardados: no implica que sigan siendo válidos ante el backend. */
  isAuthenticated: boolean;
  login: (tokens: TokenPair) => void;
  /**
   * Cierra la sesión: limpia los tokens al instante y revoca el refresh token en
   * el backend en segundo plano (best-effort: si falla, el token vence solo).
   */
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Sesión de la app: guarda y limpia los tokens, y reacciona si el refresh falla. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => tokenStore.hasSession());

  /** Limpia la sesión solo en el navegador (sin llamar al backend). */
  const limpiarSesion = useCallback(() => {
    tokenStore.clear();
    setIsAuthenticated(false);
  }, []);

  const logout = useCallback(() => {
    const refreshToken = tokenStore.getRefreshToken();
    limpiarSesion();
    if (refreshToken) {
      // El error se ignora a propósito: la sesión local ya quedó cerrada y el
      // refresh token vence solo en el backend.
      cerrarSesion(refreshToken).catch(() => undefined);
    }
  }, [limpiarSesion]);

  const login = useCallback((tokens: TokenPair) => {
    tokenStore.setTokens(tokens);
    setIsAuthenticated(true);
  }, []);

  // Si el refresh falla, el backend ya rechazó el token: basta con limpiar en local.
  useEffect(() => {
    setSessionExpiredHandler(limpiarSesion);
    return () => setSessionExpiredHandler(null);
  }, [limpiarSesion]);

  const value = useMemo<AuthContextValue>(
    () => ({ isAuthenticated, login, logout }),
    [isAuthenticated, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider.');
  }
  return context;
}

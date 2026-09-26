/**
 * Persistencia de los tokens de sesión (access + refresh) en `localStorage`.
 * Es la única pieza que lee o escribe estas claves; el resto de la app pasa
 * siempre por acá para no duplicar el formato de almacenamiento.
 */

const ACCESS_TOKEN_KEY = 'ocrRag.auth.accessToken';
const REFRESH_TOKEN_KEY = 'ocrRag.auth.refreshToken';

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export const tokenStore = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens(tokens: TokenPair): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  },

  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  hasSession(): boolean {
    return this.getAccessToken() !== null;
  },
};

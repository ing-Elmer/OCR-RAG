---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

# Frontend — React + TypeScript

Stack: npm (no pnpm), React + TS `strict` con `noUnusedLocals`/`noUnusedParameters`, Vite,
Tailwind v4 CSS-first (sin `tailwind.config.js`), react-router-dom v7, axios.

## Estructura (`src/`)
```
api/api.ts            instancia axios (auth + interceptor de refresh) y publicApi
api/endpoints.ts      única fuente de rutas REST, agrupadas por dominio
api/tokenStore.ts     persistencia de tokens
services/ApiClient.ts request<T>() — desenvuelve el envelope y lanza ApiError
services/<Feature>Service.ts
hooks/use<Feature>.ts
types/<feature>.ts
pages/<Feature>/      páginas
components/<Feature>/ UI de la feature
components/ui/        componentes compartidos (tabla, modal, estados, formularios)
helpers/<Feature>/mappers.ts   DTO ↔ modelo de UI (si hace falta)
context/              AuthContext (sesión) y UserContext (perfil, rol, permisos)
routes/               PrivateRoute / PublicRoute
utils/
```

## Reglas
- Imports propios con alias `@/...`; **nunca** rutas relativas `../`.
- URLs solo en `api/endpoints.ts`; services usan `request<T>()`; **nunca** axios directo fuera
  de `api/api.ts`. La URL base sale de `import.meta.env.VITE_API_URL`, nunca hardcodeada.
- Nueva página autenticada: entrada en la navegación + `<Route>` protegida con el mismo gate de
  permisos (`permissionCode` / `roles`), evaluado por una única función compartida.
- Sesión (tokens) en `AuthContext`; rol y permisos en `UserContext`, resueltos desde el backend
  (`/api/me`), no desde el JWT. `hasPermission()` es solo UX: el backend revalida.
- Prohibido: `any`, `@ts-ignore`, `@ts-expect-error`, `as unknown as`, `console.log`.
- Mensajes de UI en español; errores técnicos se reemplazan por un mensaje genérico.

## Piezas compartidas (mejora: no duplicar)
- Fetching: `useAsyncResource<T>(loader)` → `{ data, isLoading, error, reload }`. Los hooks de
  feature lo usan en vez de repetir `isLoading`/`error`/`reload`.
- Tablas: un único `DataTable` en `components/ui/` (basado en `@tanstack/react-table`) con estado
  vacío incluido; no tablas armadas a mano en cada feature.
- Errores de formulario: una utilidad `toFormErrors(err)` compartida.
- Un mismo tipo de visor/modal no se implementa dos veces: se extiende el existente.

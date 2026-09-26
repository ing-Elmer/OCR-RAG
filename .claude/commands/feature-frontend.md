---
description: Crea un módulo de feature frontend según el estándar (types, endpoint, service, hook, componentes, página, ruta)
argument-hint: <NombreFeature> <descripción / endpoint que consume>
---

Creá la feature frontend: **$ARGUMENTS**

Usá el agente `frontend-react`. Tomá la ruta del frontend y los roles/permisos del
**perfil del proyecto**.

Piezas esperadas:
- `types/<feature>.ts`, rutas en `api/endpoints.ts`, `services/<Feature>Service.ts`
- `hooks/use<Feature>.ts` sobre `useAsyncResource`
- `components/<Feature>/…` usando `DataTable` y los estados compartidos, y `pages/<Feature>/<Feature>Page.tsx`
- Entrada en la navegación + `<Route>` protegida con el permiso correspondiente
- Test de Vitest del hook o de la lógica no trivial

Si falta alguna pieza compartida (`useAsyncResource`, `DataTable`, estados), creala primero en
su lugar compartido. Si el endpoint del backend no existe, frená y devolvé el contrato requerido.
Al final corré `npm run build` y `npm run test`.

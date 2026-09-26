---
description: Revisa los cambios contra las reglas del estándar (capas, ApiResponse, datos, frontend, seguridad, tests)
argument-hint: [rama base]  (vacío = cambios locales contra HEAD)
allowed-tools: Read, Glob, Grep, Bash(git diff*), Bash(git status*), Bash(git log*)
---

Estado actual:
!`git status --short`

Archivos modificados respecto de HEAD:
!`git diff --stat HEAD`

Revisá el diff (`git diff $ARGUMENTS`, o `git diff HEAD` si no pasé rama base) contra
`.claude/rules/` y las excepciones del perfil del proyecto. Buscá especialmente:

- **Backend:** lógica de negocio en `api` o `infrastructure`, SQL fuera de `repositories/`,
  imports que rompen las capas, uso de ORM, endpoints que devuelven el DTO/`dict` sin
  `ApiResponse`, `try/except` o `HTTPException` en routers, excepciones sin `status_code`,
  SQL con f-strings/`format`/concatenación, logging en repositorios, JWT decodificado fuera de
  `get_current_user`, `os.getenv` suelto, I/O bloqueante en `async def`, `print`, escrituras en
  conexiones de solo lectura, endpoints públicos sin justificar, DTOs que no heredan de
  `CamelModel`, `# type: ignore` sin justificar.
- **Frontend:** imports `../`, axios fuera de `api/api.ts`, URLs fuera de `endpoints.ts`,
  `any` / `@ts-ignore` / `console.log`, página sin gate de permisos, fetching o tablas duplicadas
  en vez de las piezas compartidas.
- **GitHub Actions:** workflow sin `permissions:` mínimo, actions de terceros sin fijar por SHA,
  secretos o `${{ github.event.* }}` interpolados en `run:`, `pull_request_target` con checkout
  del PR, CI que no corre los mismos pasos que `/verificar`, jobs sin `timeout-minutes`.
- **SQL:** número de script repetido, constraints sin nombre, DML y DDL mezclados.
- **General:** secretos, archivos temporales o logs agregados, tests borrados o salteados, lógica
  nueva sin tests.

Salida: lista ordenada por severidad (🔴 bloqueante, 🟡 corregir, 🔵 sugerencia) con
`archivo:línea`, el problema y la corrección propuesta. **No edites nada.**

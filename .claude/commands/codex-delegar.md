---
description: Delega una tarea de código a Codex (codex exec) y Claude verifica el resultado con build, tests y reglas
argument-hint: <tarea a delegar>
allowed-tools: Read, Glob, Grep, Bash(git diff*), Bash(git status*), Bash(codex exec*), Bash(codex --version*), Bash(uv run *), Bash(npm run *)
---

Tarea: $ARGUMENTS

Estado actual (para distinguir después qué tocó Codex):
!`git status --short`

## 1. Antes de delegar
- Si no hay tarea, pedila y pará.
- Leé el `## Perfil del proyecto` de `CLAUDE.md` y las reglas de `.claude/rules/` que aplican.
- Si la tarea toca **backend y frontend**, fijá primero el contrato (DTOs, endpoint, códigos de
  error, permiso), igual que con los subagentes.
- **No delegues** tareas que requieran ejecutar SQL, manejar secretos, hacer push/merge o
  cambiar configuración de deploy: esas no se delegan a nadie.
- Si hay cambios sin commitear en los archivos que va a tocar Codex, avisá al usuario antes:
  después no se podrían separar.

## 2. Prompt para Codex
Codex arranca sin contexto y **no lee `CLAUDE.md` por su cuenta**. El prompt tiene que ser
autosuficiente e incluir:

1. La tarea concreta y el criterio de "terminado".
2. Los valores del perfil que aplican (paquete, schema, prefijo, conexiones, rutas).
3. Qué reglas de `.claude/rules/` debe leer antes de empezar, por nombre de archivo.
4. El contrato, si lo hay, y los archivos existentes a tomar como referencia de estilo.
5. Los límites, siempre: no ejecutar SQL, no hacer `git commit`/`push`, no crear ni leer `.env`,
   no escribir secretos, no agregar dependencias sin decirlo, no borrar ni saltear tests, todo
   en español.
6. Qué verificar antes de terminar (los mismos comandos de `/verificar` del área tocada) y qué
   devolver: archivos tocados y resultado real de los comandos.

Escribí el prompt en un archivo del **scratchpad de la sesión** (nunca en el repo) y ejecutá,
desde la raíz del repo, en background y con timeout amplio:

```
codex exec -s workspace-write --ephemeral -C <raíz del repo> -o <scratchpad>/codex-respuesta.md - < <scratchpad>/codex-prompt.md
```

Nunca uses `--dangerously-bypass-approvals-and-sandbox` ni `-s danger-full-access`.

## 3. Verificación (obligatoria: el reporte de Codex no alcanza)
1. `git status --short` y `git diff`: qué archivos tocó realmente. Si tocó algo fuera del
   alcance, avisalo.
2. Corré vos los checks del área tocada (backend: `ruff check`, `ruff format --check`, `mypy`,
   `lint-imports`, `pytest`; frontend: `npm run build`, `npm run test`, `npm run lint`).
3. Revisá el diff contra `.claude/rules/` como en `/revisar`, prestando especial atención a los
   tests: que existan, que prueben lo pedido y que no se hayan debilitado.
4. Si algo falla o viola una regla, corregilo vos o delegá la corrección con un prompt nuevo,
   máximo **una** vuelta más a Codex. Si sigue mal, reportalo en vez de insistir.

## 4. Reporte
Qué pidió el usuario, qué hizo Codex (archivos), qué verificaste con su resultado real, qué
corregiste vos y qué quedó pendiente. Dejá explícito qué partes escribió Codex.

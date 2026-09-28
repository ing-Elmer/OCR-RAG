---
description: Segunda opinión — Codex revisa los cambios en solo lectura y Claude consolida sus hallazgos con los propios
argument-hint: [rama base]  (vacío = cambios sin commitear)
allowed-tools: Read, Glob, Grep, Bash(git diff*), Bash(git status*), Bash(git log*), Bash(codex exec*), Bash(codex --version*)
---

Estado actual:
!`git status --short`

Versión de Codex:
!`codex --version`

## 1. Revisión de Codex (solo lectura)
Ejecutá la revisión desde la raíz del repo, en background y con un timeout amplio (puede
tardar varios minutos). Guardá el prompt y la salida en el scratchpad de la sesión, **nunca
dentro del repo**.

**Importante:** `codex review --uncommitted` y `codex review --base` **no aceptan
instrucciones personalizadas** (Codex 0.157: "the argument '--uncommitted' cannot be used
with '[PROMPT]'"). Sin las instrucciones, Codex revisa sin conocer el estándar. Por eso se
usa `codex exec` en sandbox de solo lectura, con el prompt por stdin:

```
codex exec -s read-only --ephemeral -C <raíz del repo> -o <scratchpad>/codex-review.md - < <scratchpad>/codex-prompt-review.md
```

El prompt le indica qué diff revisar:
- Sin argumento → los cambios sin commitear: `git diff HEAD` más los archivos nuevos
  (`git status --porcelain`, líneas `??`).
- Con rama base (`$ARGUMENTS`) → `git diff $ARGUMENTS...HEAD`.

Después, las instrucciones de revisión. Codex no lee `CLAUDE.md` por su cuenta, así que se lo
indicamos:

> Revisá estos cambios contra el estándar del proyecto. Antes de opinar, leé la sección
> "Perfil del proyecto" y "Excepciones al estándar" de CLAUDE.md, y las reglas en
> .claude/rules/ (backend-arquitectura, backend-api, backend-datos, sql-migraciones,
> frontend-react, frontend-estilos, testing, seguridad-config, ci-github). Priorizá bugs de
> correctitud, seguridad y concurrencia por encima del estilo. Para cada hallazgo indicá
> archivo:línea, el problema, un escenario concreto que lo dispare y la corrección. No
> reportes nada que no puedas señalar en el código. Respondé en español.

Si Codex falla (sin login, proxy, timeout), reportá el error tal cual y seguí solo con el paso 2.

## 2. Revisión propia
En paralelo, hacé la revisión de `/revisar` sobre el mismo diff (mismas reglas, mismo alcance).

## 3. Consolidación
**Verificá cada hallazgo de Codex en el código** antes de incluirlo: Codex puede equivocarse
o no conocer una excepción del perfil. Clasificalo como:

- ✅ **Confirmado**: lo verificaste en el código.
- ➕ **Solo Claude**: lo encontraste vos y Codex no.
- ❌ **Descartado**: falso positivo o contradice una excepción del perfil. Explicá por qué en
  una línea.

Salida: una sola lista ordenada por severidad (🔴 bloqueante, 🟡 corregir, 🔵 sugerencia) con
`archivo:línea`, problema, corrección propuesta y origen (Codex / Claude / ambos). Cerrá con
una línea que diga cuántos hallazgos aportó cada uno y cuántos coincidieron.

**No edites nada.** Si el usuario pide aplicar las correcciones, eso es un paso aparte.

---
description: Propone un mensaje de commit en español a partir de los cambios y commitea tras confirmación
argument-hint: [clave de ticket]
allowed-tools: Bash(git status*), Bash(git diff*), Bash(git log*), Bash(git add*), Bash(git commit*)
---

Estado:
!`git status --short`

Cambios staged:
!`git diff --cached --stat`

Últimos commits (para imitar el estilo):
!`git log --oneline -8`

1. Si no hay nada staged, proponé qué archivos agregar (excluí logs, temporales, respuestas de
   prueba, `publish/`, `bin/`, `obj/`, `dist/`) y esperá mi confirmación.
2. Redactá el mensaje en español, en el estilo de los commits anteriores, incluyendo el ticket
   **$ARGUMENTS** si lo pasé (o el que aparezca en el nombre de la rama). Primera línea de 72
   caracteres como máximo y, si no es obvio, un cuerpo que explique el porqué.
3. Mostrame el mensaje y **esperá mi OK** antes de `git commit`.
4. Nunca `git push`.

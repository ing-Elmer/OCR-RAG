---
description: Genera la descripción del Pull Request para la rama actual
argument-hint: [rama destino]  (vacío = rama base del perfil del proyecto)
allowed-tools: Read, Grep, Bash(git diff*), Bash(git log*), Bash(git branch*), Bash(git rev-parse*), Bash(gh pr view*), Bash(gh pr list*)
---

Rama actual: !`git rev-parse --abbrev-ref HEAD`

Rama destino: **$ARGUMENTS** (si está vacío, la rama base que declara el perfil del proyecto).
Calculá `git log --oneline <destino>..HEAD` y `git diff --stat <destino>...HEAD`.

Si el repo tiene `.github/pull_request_template.md`, seguí sus secciones. Si no, escribí la
descripción del PR en español y en markdown:

- **Resumen:** qué y por qué (1 a 3 líneas), con el ticket de Jira si aparece en la rama o en
  los commits.
- **Cambios:** backend / frontend / SQL. Listá los scripts SQL nuevos en el orden en que hay que
  ejecutarlos antes del deploy.
- **Cómo probar:** pasos concretos, con el rol a usar.
- **Riesgos / notas de deploy:** migraciones, configuración o secretos nuevos que hay que cargar
  en el ambiente, cambios que rompen el contrato con el frontend.

Devolvé el texto listo para pegar. Si la rama ya está publicada en GitHub (`gh pr view` no
encuentra un PR y la rama existe en el remoto), ofrecé crearlo como borrador con
`gh pr create --draft --base <destino> --title "..." --body-file <archivo en el scratchpad>`
y **esperá mi OK**. Nunca hagas push, merge, aprobación ni marques el PR como listo.

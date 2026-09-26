---
description: Crea el próximo script SQL numerado en la carpeta de scripts del proyecto (sin ejecutarlo)
argument-hint: <descripción del cambio>
---

Creá el script SQL para: **$ARGUMENTS**

1. Tomá la carpeta de scripts, el schema y el prefijo de tablas del **perfil del proyecto**.
2. Listá la carpeta y calculá el próximo número libre. Si detectás números duplicados, avisame.
3. Escribí el script siguiendo `.claude/rules/sql-migraciones.md` y el estilo del último script
   del mismo tipo.
4. Si el cambio impacta repositorios o DTOs (schemas Pydantic) existentes, listá qué archivos habría que tocar
   (sin modificarlos).
5. **No ejecutes el script.** Mostrame el nombre del archivo y su contenido.

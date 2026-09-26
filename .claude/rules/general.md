# Reglas generales del estándar (siempre activas)

## Perfil del proyecto
- Antes de crear archivos, nombrar proyectos, tablas o conexiones, leer la sección
  `## Perfil del proyecto` del `CLAUDE.md` raíz. **Nunca** asumir nombres, rutas, schemas ni
  puertos: salen del perfil. Si falta un dato, preguntarlo (o sugerir `/adoptar`).
- En estas reglas, `<app>` (paquete Python), `<schema>` y `<prefijo>_` son los valores del perfil.
- Si el perfil declara una excepción al estándar, respetarla.

## Forma de trabajar
- Idioma de respuestas, comentarios, docs, mensajes de UI y commits: **español**.
- Antes de crear algo nuevo, buscar en el proyecto una pieza equivalente y seguir su estilo; si
  el código existente contradice el estándar, seguir el estándar y avisarlo.
- Antes de dar una tarea por terminada, compilar y correr los tests del área tocada y reportar el
  resultado real (nunca "debería funcionar").
- No crear archivos temporales (tokens, respuestas JSON, logs) dentro del repo: usar el scratchpad.

## Límites
- **Nunca** `git push`, merge, rebase de ramas compartidas ni aprobar PRs.
- **Nunca** ejecutar SQL contra una base de datos sin confirmación explícita del usuario.
- **Nunca** escribir secretos (passwords, connection strings con credenciales, signing keys,
  API keys) en código, docs, logs ni en permisos de `.claude/settings*.json`.

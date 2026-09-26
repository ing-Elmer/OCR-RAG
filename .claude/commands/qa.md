---
description: Prueba un flujo de la app en el navegador con el agente QA (Playwright)
argument-hint: <flujo a probar>  (ej. "crear un registro con el rol X y verlo en su bandeja")
---

Delegá en el agente `qa` la prueba de este flujo: **$ARGUMENTS**

- Si la app no está levantada, levantala primero (igual que `/levantar`).
- Pedime usuarios de prueba si hacen falta; nunca uses credenciales de producción.
- Devolveme el reporte del agente: pasos ejecutados, resultado y hallazgos con severidad y
  screenshots.

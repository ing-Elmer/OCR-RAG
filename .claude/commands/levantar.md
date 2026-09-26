---
description: Levanta backend y frontend en background para probar localmente
argument-hint: [backend | frontend]  (vacío = ambos)
---

Levantá el entorno local. Alcance: **$ARGUMENTS** (si está vacío: backend y frontend).
Tomá las rutas, los puertos, el paquete `<app>` y el health check del **perfil del proyecto**.

1. Revisá si los puertos ya están en uso. Si hay un proceso ocupándolos, decime el PID y el
   nombre y **preguntá** antes de detenerlo.
2. Backend: en su carpeta, `uv run uvicorn <app>.api.main:app --reload --port <puerto>` en
   background. La configuración sale del `backend/.env` local; si no existe, avisame y mostrame
   qué variables pide `.env.example` (nunca inventes valores de secretos).
3. Frontend: `npm run dev` en background.
4. Esperá a que respondan (health check del backend y raíz del frontend) y decime las URLs.
5. Los logs van al scratchpad, nunca dentro del repo.

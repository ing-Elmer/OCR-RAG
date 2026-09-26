---
description: Lee un ticket de Jira, arma el plan y lo implementa delegando en los agentes
argument-hint: <CLAVE-TICKET>
---

Trabajá el ticket de Jira **$ARGUMENTS**.

1. Leé el ticket con el MCP de Atlassian: descripción, criterios de aceptación, subtareas,
   comentarios y links. Si el MCP no está autenticado, avisame y frená.
2. Leé el perfil del proyecto y explorá el código relacionado. Resumime:
   - Qué pide el ticket y qué ya existe.
   - Contrato propuesto (DTOs, endpoints, permisos, scripts SQL) si cruza backend y frontend.
   - Archivos a crear o modificar.
   - Dudas o ambigüedades del ticket.
3. **Esperá mi confirmación** antes de implementar.
4. Implementá delegando en `backend-python` / `frontend-react` y cerrá con `qa` si hay UI.
5. Verificá con build y tests, y dame el resumen: hecho, verificado y pendiente.
   No comentes ni muevas el ticket en Jira sin que te lo pida.

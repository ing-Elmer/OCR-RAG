# 07 · Riesgos y pendientes

## Riesgos

| Riesgo | Impacto | Probabilidad | Mitigación |
|---|---|---|---|
| **Normas desactualizadas:** los textos cargados son de 2008 y no incluyen reformas | Alto: el sistema puede citar una redacción que ya cambió, con total seguridad | Alta | Que un especialista aduanero liste las reformas vigentes y sumarlas al corpus; mientras tanto, advertir a los usuarios |
| **Respuesta inventada** cuando la información no está en el corpus | Alto | Media | El prompt lo prohíbe y hay una regla que no llama al modelo si no hay fuentes relevantes, pero **todavía no se mide**: faltan casos negativos en la evaluación |
| **Datos de clientes enviados a OpenAI** | Alto si la política de la empresa no lo permite | A confirmar | Validar con el área legal o de seguridad; la API de OpenAI no usa estos datos para entrenar por defecto |
| **Uso de las respuestas como asesoría vinculante** | Medio | Media | Dejar claro en la interfaz que es una herramienta de apoyo y que la cita permite verificar |
| **CI frenado** por la facturación de GitHub | Bloquea merges y despliegue | Actual | Resolver la facturación de la cuenta |
| **Cambios que empeoran la calidad sin que nadie lo note** | Medio | Media | Correr `evaluar` antes y después de cada cambio (ver [04](04-corpus-y-evaluacion.md)) |
| **Costo de OpenAI** al crecer el corpus | Bajo hoy | Baja | Embeddings solo al cargar o reprocesar, sin duplicados por hash; `--dry-run` en el corpus |

## Pendientes

### Para cerrar lo hecho
- [ ] Resolver la facturación de GitHub y mergear las tres ramas en orden: configuración →
      pipeline → Fase 1.
- [ ] Sumar **casos negativos** a la evaluación.
- [ ] Validar y cargar las **reformas** vigentes del CAUCA IV y del RECAUCA IV.

### Para la Fase 2
- [ ] Juntar entre **20 y 30 documentos reales** de embarque (BL, facturas, packing lists, DUCA),
      con datos sensibles tachados si hace falta.
- [ ] Definir con el área operativa qué campos importan de cada tipo de documento.

### Mejoras menores
- [ ] Mensajes de validación en español: hoy salen los de Pydantic, en inglés.
- [ ] Que el frontend avise claramente cuando falta `VITE_API_URL`.
- [ ] Límite de intentos de login fallidos.
- [ ] Endpoint para borrar documentos (hoy se borran por SQL).
- [ ] Fijar `ubuntu-24.04` en el CI: `ubuntu-latest` pasa a Ubuntu 26 en octubre de 2026.
- [ ] Decidir si `agent-view.vsix` debe seguir versionado en la raíz del repo.

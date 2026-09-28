# 02 · Fases del proyecto

Cada fase tiene un objetivo, un alcance, entregables y **criterios de aceptación medibles**. Una
fase se da por cerrada cuando sus criterios se verifican, no cuando "el código está".

| Fase | Nombre | Estado | Rama / commit |
|---|---|---|---|
| — | Configuración inicial | ✅ Hecha | `feature/configuracion-inicial` · `a45e2c3` |
| 0 | Pipeline OCR + RAG | ✅ Hecha | `feature/pipeline-ocr-rag` · `c86ea4f` |
| 1 | RAG experto en normativa | ✅ Hecha | `feature/fase1-rag-experto` · `dad3b7c` |
| 2 | Extracción estructurada de documentos de embarque | ⏳ Próxima | — |
| 3 | Validación cruzada por embarque | 📋 Planificada | — |
| 4 | Evaluación continua | 🟡 Iniciada | — |
| D | Despliegue (Railway + Vercel) | 📋 Planificada | — |

> Las tres ramas hechas están **apiladas** (cada una sale de la anterior) y todavía no se
> mergearon a `Develop`: el CI de GitHub está frenado por un problema de facturación de la
> cuenta. Hay que mergearlas en orden.

---

## Configuración inicial ✅

**Objetivo:** dejar una base verificada sobre la que construir.

**Entregables**
- Backend FastAPI en 4 capas (`api`, `application`, `core`, `infrastructure`), con un contrato de
  capas que valida `import-linter`.
- Respuesta estándar `ApiResponse`, errores centralizados (400 en lugar de 422).
- Autenticación: JWT de acceso de 15 minutos y refresh token de 7 días, rotado en cada uso.
  Reusar un refresh ya revocado revoca toda la sesión del usuario.
- Roles ADMIN, OPERADOR y LECTOR. CLI `crear-admin` para el primer usuario.
- Frontend React + TypeScript strict con interceptor de refresh, rutas protegidas por permiso y
  componentes base.
- CI de GitHub Actions (`ci-backend`, `ci-frontend`), Dockerfile para Railway y `vercel.json`.

**Aceptación:** los tests de autenticación y autorización pasan (401 sin token, 403 sin permiso,
reuso de refresh revocado). ✅

---

## Fase 0 · Pipeline OCR + RAG ✅

**Objetivo:** que un documento cargado se pueda consultar en lenguaje natural.

**Entregables**
- Carga de PDF e imágenes, guardados en PostgreSQL (`bytea`).
- Procesamiento en segundo plano: extracción de texto (nativo con pypdfium2, OCR con Tesseract
  solo si la página no tiene texto), fragmentación, embeddings de OpenAI y almacenamiento en
  pgvector. Si la app se reinicia, retoma los documentos pendientes.
- Consultas con respuesta del modelo basada solo en los fragmentos recuperados, con citas
  numeradas.
- Carga masiva del corpus normativo (`cargar-corpus`): descarga segura, sin duplicados y con
  link a la fuente original.
- Pantallas de Documentos y Consultas. Backend en Docker Compose.

**Aceptación:** una pregunta sobre un documento cargado devuelve una respuesta con fuentes que
se pueden verificar. ✅

**Lo que aprendimos:** la primera respuesta real ("¿Qué es el tránsito aduanero?") tenía tres
problemas. Citaba artículos **derogados**, porque la edición del CAUCA que se había cargado
mezclaba tres normas distintas. No encontraba la definición. Y el texto venía con palabras
partidas. Esas fallas definieron la Fase 1. Ver [04 · Corpus](04-corpus-y-evaluacion.md).

---

## Fase 1 · RAG experto en normativa ✅

**Objetivo:** que las respuestas sobre normativa aduanera sean correctas, completas y
verificables por artículo.

**Entregables**
- **Búsqueda híbrida:** semántica (pgvector) más búsqueda por palabras clave en español
  (PostgreSQL), fusionadas con Reciprocal Rank Fusion.
- **Fragmentación por artículo:** un fragmento nunca mezcla dos artículos, y cada uno sabe a qué
  norma y artículo pertenece. Distingue los encabezados de las referencias internas ("según el
  artículo 94 de este Código").
- **Limpieza** de encabezados y pies de página del PDF.
- **Prompt de especialista** en aduanas de Centroamérica, con un ejemplo concreto de cita.
- **Tipo de documento y norma:** clasificación automática con el LLM, corrección manual y filtro
  en las consultas.
- **Procesamiento seguro ante concurrencia:** un documento no lo procesan dos procesos a la vez,
  y un procesamiento viejo no pisa uno nuevo.
- **Evaluación automática** (`evaluar`) con un set de 16 casos, y comando `reprocesar`.

**Criterios de aceptación y resultado**

| Criterio | Meta | Resultado |
|---|---|---|
| Artículos detectados en CAUCA IV | 134 / 134 | ✅ 134 / 134 |
| Artículos detectados en RECAUCA IV | 646 / 646, sin saltos de numeración | ✅ 646 / 646 |
| hit@k del set de evaluación | ≥ 90 % | ✅ 100 % |
| Citas completas (norma + artículo) | ≥ 70 % | ✅ 81 % (antes 6 %) |
| Revisión cruzada con Codex | hallazgos bloqueantes corregidos | ✅ 8 hallazgos verificados y corregidos |

---

## Fase 2 · Extracción estructurada ⏳

**Objetivo:** que de cada documento de embarque salgan sus datos en forma estructurada, listos
para consultar y cruzar.

**Alcance propuesto**
- Esquemas por tipo de documento:
  - **Bill of Lading / AWB:** embarcador, consignatario, notificado, puertos de carga y descarga,
    buque o vuelo, contenedores, bultos, peso bruto, volumen.
  - **Factura comercial:** vendedor, comprador, Incoterm, moneda, ítems (descripción, cantidad,
    precio, partida), total.
  - **Packing list:** bultos, pesos neto y bruto por ítem, marcas.
  - **DUCA:** régimen, aduanas, partidas SAC, valores, tributos.
- Extracción con salida estructurada del LLM sobre el texto del OCR, guardada en tablas propias.
- **Validaciones automáticas:** dígito verificador de contenedor (ISO 6346), partida existente en
  el SAC, Incoterm válido, sumas de pesos y cantidades.
- Pantalla de revisión y corrección de lo extraído.

**Requisito previo:** entre 20 y 30 documentos reales variados (BL, facturas, packing lists,
DUCA), con los datos sensibles tachados si hace falta. Sin ellos no se puede medir la calidad.

**Criterios de aceptación propuestos:** ≥ 90 % de campos correctos en los documentos del set; el
dígito verificador de contenedor detecta el 100 % de los números inválidos del set.

---

## Fase 3 · Validación cruzada por embarque 📋

**Objetivo:** detectar inconsistencias entre los documentos de un mismo embarque antes de que
lleguen a la aduana.

**Alcance propuesto**
- Agrupar documentos en un **expediente** por embarque.
- Reglas de cruce: pesos y bultos (factura ↔ packing list ↔ BL), contenedores (BL ↔ DUCA),
  valores e Incoterm (factura ↔ DUCA), partidas (factura ↔ DUCA).
- Informe de inconsistencias por expediente, con el dato de cada documento en conflicto.

**Criterios de aceptación propuestos:** en un set de expedientes con errores sembrados, detecta
≥ 95 % de las inconsistencias con ≤ 5 % de falsas alarmas.

---

## Fase 4 · Evaluación continua 🟡

**Objetivo:** que cada cambio (prompt, modelo, chunking, corpus) se mida antes de aceptarse.

**Hecho:** comando `evaluar`, set de 16 casos sobre CAUCA IV y RECAUCA IV, línea base registrada.

**Pendiente**
- **Casos negativos:** preguntas cuya respuesta no está en el corpus, para medir si el sistema
  inventa.
- Casos sobre documentos reales de embarque (con la Fase 2).
- Correr la evaluación en CI como chequeo informativo, no bloqueante, para seguir su evolución.

---

## Despliegue 📋

**Objetivo:** que el sistema esté disponible para el equipo fuera de una máquina de desarrollo.

**Alcance**
- **Backend en Railway:** servicio desde el repo con Root Directory `/backend`, *Wait for CI* y
  base PostgreSQL con pgvector.
- **Frontend en Vercel:** Root Directory `frontend`, `VITE_API_URL` por ambiente.
- **Configuración de producción:** CORS con el dominio de Vercel, scripts SQL 001 a 011
  ejecutados en la base de Railway y corpus cargado.

**Bloqueante hoy:** la facturación de GitHub (sin CI no hay merge ni despliegue). Checklist
completo en [05 · Operación](05-operacion.md#despliegue).

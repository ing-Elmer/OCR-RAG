# OCR-RAG — Documentación del proyecto

Asistente experto en **logística, comercio exterior y aduanas de Centroamérica**. Lee documentos
(PDF digitales o escaneados, imágenes), extrae su texto con OCR cuando hace falta y responde
preguntas en lenguaje natural **citando la norma y el artículo** de donde sale cada afirmación.

> Estado al 2026-09-27: **Fase 1 terminada** (RAG experto sobre normativa). La búsqueda encuentra
> el artículo correcto en el 100 % de los casos del set de evaluación, y el 81 % de las
> respuestas lo cita con norma y artículo. Todavía no hay despliegue: corre en local con Docker.

## Cómo leer esta carpeta

| Documento | Para qué sirve | Quién debería leerlo |
|---|---|---|
| [01 · Visión y alcance](01-vision-y-alcance.md) | Qué problema resuelve, para quién, qué entra y qué no | Todos |
| [02 · Fases del proyecto](02-fases.md) | Hoja de ruta: qué se hizo, qué sigue y cómo se acepta cada fase | Todos |
| [03 · Arquitectura](03-arquitectura.md) | Componentes, flujo de datos, modelo de datos y API | Desarrollo |
| [04 · Corpus y evaluación](04-corpus-y-evaluacion.md) | Qué normas conoce el sistema, cómo se verificaron y cómo se mide la calidad | Desarrollo, negocio |
| [05 · Operación](05-operacion.md) | Levantar el entorno, scripts SQL, comandos y problemas conocidos | Desarrollo |
| [06 · Decisiones](06-decisiones.md) | Por qué se eligió cada cosa, con las alternativas descartadas | Desarrollo, líder técnico |
| [07 · Riesgos y pendientes](07-riesgos-y-pendientes.md) | Qué puede salir mal y qué falta | Líder técnico, negocio |

## En una página

- **Qué hace hoy:** cargás un documento, el sistema lo procesa en segundo plano (texto nativo u
  OCR, fragmentos por artículo, embeddings) y después respondés preguntas sobre él. Ya trae cargada
  la normativa aduanera regional vigente: CAUCA IV, RECAUCA IV y el Convenio Arancelario y
  Aduanero Centroamericano.
- **Cómo responde:** combina búsqueda semántica y por palabras clave, y le pasa los fragmentos más
  relevantes a un modelo de lenguaje. Ese modelo solo puede usar esos fragmentos y tiene que citar
  "Art. N de la norma [n]".
- **Stack:** Python + FastAPI + PostgreSQL con pgvector en el backend, React + TypeScript + Vite
  en el frontend, Tesseract para el OCR y OpenAI para embeddings y respuestas.
- **Qué sigue:** leer documentos de embarque (BL, facturas, packing lists, DUCA) y extraer sus
  datos en forma estructurada (Fase 2), y cruzarlos para detectar inconsistencias (Fase 3).

## Relación con otros archivos del repo

- [`CLAUDE.md`](../CLAUDE.md): perfil técnico del proyecto para los agentes de desarrollo
  (nombres, rutas, conexiones, variables, deuda). Es la fuente de verdad de los datos operativos;
  estos documentos lo resumen y lo explican, pero no lo reemplazan.
- [`.claude/rules/`](../.claude/rules/): el estándar de desarrollo que sigue el código.
- [`backend/db/`](../backend/db/): scripts SQL numerados, en el orden en que se ejecutan.

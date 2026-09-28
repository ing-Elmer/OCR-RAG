# 04 · Corpus y evaluación

El sistema **no se entrena**. Sabe exactamente lo que está cargado en la base de documentos
(el *corpus*). La calidad de las respuestas depende de dos cosas: que el corpus sea correcto y
vigente, y que la búsqueda encuentre el fragmento justo. Este documento explica cómo se cuida y
se mide cada una.

## Corpus normativo cargado

Definido en `backend/src/ocr_rag/cli/corpus/normativa_centroamerica.toml` y cargado con
`cargar-corpus`.

| Id | Norma | Fuente | Contenido verificado |
|---|---|---|---|
| `cauca-iv` | **CAUCA IV**, Res. 223-2008 (COMIECO-XLIX) | [FAOLEX](https://faolex.fao.org/docs/pdf/sica205668.pdf) | 34 páginas, arts. 1 a 134 |
| `recauca-iv` | **RECAUCA IV**, Res. 224-2008 (COMIECO-XLIX) | [FAOLEX](https://faolex.fao.org/docs/pdf/sica205787.pdf) | 217 páginas, arts. 1 a 646 |
| `convenio-arancelario-aduanero` | Convenio sobre el Régimen Arancelario y Aduanero Centroamericano, con sus tres protocolos | [SIECA vía SDE Honduras](https://sde.gob.hn/wp-content/uploads/2017/08/Convenio-Arancelario-y-Aduanero-Centroamericano.pdf) | 13 páginas |

### Fuentes descartadas, y por qué

| Fuente | Motivo |
|---|---|
| Edición "CAUCA y RECAUCA" de la Imprenta Nacional de Costa Rica (2016) | El título promete CAUCA IV + RECAUCA, pero el PDF **compila tres instrumentos**: CAUCA III derogado (págs. 11–33), CAUCA IV (35–67) y el **reglamento viejo** del CAUCA III (Res. 101-2002, págs. 69–133). Se cargó al principio, y el sistema terminó citando artículos derogados. |
| CAUCA de SEFIN Honduras | Es el CAUCA III (Acuerdo 023-2003), derogado. |
| CAUCA de aduanas.gob.hn | El servidor rechaza las descargas automáticas (403). |
| Convenio de transparencia.mh.gob.sv | Es el mismo documento que el de SIECA; cargarlo duplicaría los resultados. |

### Regla para sumar una fuente

**Verificar el contenido página por página, no el título.** Antes de agregarla al manifiesto:
1. Qué resolución o instrumento contiene realmente, buscando el texto en el PDF.
2. Qué rango de artículos trae, y si hay retrocesos en la numeración, que indican dos normas
   mezcladas.
3. Si el texto es nativo o escaneado, y si se extrae sin palabras partidas.
4. Anotar la fecha de verificación en el campo `verificado` del manifiesto.

### Limitaciones del corpus actual

- Los textos de FAOLEX son las **versiones originales de 2008**. **No incluyen reformas
  posteriores** (por ejemplo, las resoluciones 248-2009 y 261-2010 que aparecían en la edición
  de Costa Rica). Hace falta que alguien del área aduanera valide qué reformas aplican hoy.
- Solo normativa **regional**: faltan las leyes nacionales, el arancel SAC y las guías de la
  DUCA.

## Cómo se procesa una norma

1. **Extracción:** pypdfium2 lee la capa de texto. Se eligió sobre pypdf porque parte mucho menos
   las palabras: en el RECAUCA IV pypdf dejó 566 palabras cortadas ("régi men") y pypdfium2, 32.
2. **Limpieza:** se borran los encabezados y pies que se repiten en los márgenes de al menos la
   mitad de las páginas, y siempre la numeración ("Página 130 de 215"). Los encabezados de
   artículo nunca se borran.
3. **Fragmentación por artículo:** se corta en cada encabezado ("Artículo 94." y variantes).
   Las referencias internas no cortan ("…previsto en el artículo 94 de este Código…"), aunque el
   PDF las deje al inicio de una línea. Un artículo largo se divide en varios fragmentos que
   conservan el mismo número.

**Resultado verificado:** CAUCA IV 134/134 y RECAUCA IV 646/646 artículos, sin saltos de
numeración.

## Evaluación

### Qué se mide

El set `backend/src/ocr_rag/cli/evaluacion/normativa_ca.toml` tiene **16 preguntas** reales de
un operador (tránsito, transportista, OEA, garantías, faltantes y sobrantes, arribo forzoso,
mercancías peligrosas, declaración, rectificación, regímenes, abandono). Cada una lleva los
**artículos que la respuesta debe usar**, 27 en total, verificados contra el texto de cada norma.

| Métrica | Qué significa |
|---|---|
| **hit@k** | % de preguntas en las que alguno de los artículos esperados aparece entre las fuentes |
| **MRR** | Qué tan arriba aparece el primero (1 = siempre primero; 0,5 = en promedio segundo) |
| **Citas completas** | % de preguntas cuya respuesta cita **todos** los artículos esperados, con norma. "Art. 52 del CAUCA" vale; "Art. 52 del RECAUCA" no, si se esperaba el CAUCA |

### Historia de resultados

| Fecha | Cambio | hit@k | MRR | Citas completas |
|---|---|---|---|---|
| 2026-09-26 | Fase 0 (solo búsqueda semántica, sin artículos) | — | — | — ¹ |
| 2026-09-27 | Fase 1, primera corrida | 1,00 | 0,79 | 6 % |
| 2026-09-27 | Métrica corregida (aceptar "CAUCA" sin "IV"), mismas respuestas | 1,00 | 0,79 | 31 % |
| 2026-09-27 | Prompt con ejemplo concreto de cita | **1,00** | **0,79** | **81 %** |

¹ No había evaluación todavía. La prueba manual mostró que el artículo de la definición (Art. 94
del CAUCA IV) no aparecía entre las 5 primeras fuentes.

**Lectura:**
- La búsqueda está resuelta: siempre encuentra el artículo, y en 10 de 16 casos queda primero.
- Las citas saltaron cuando el prompt pasó de describir la regla a **mostrar un ejemplo**.
- El 81 % es conservador: los casos que no llegan citan otros artículos igual de válidos (por
  ejemplo, los Arts. 261 a 266 del RECAUCA en lugar del Art. 68 del CAUCA).

### Cómo usarla

- Correrla **antes y después** de cualquier cambio de prompt, modelo, chunking, búsqueda o corpus,
  y anotar el resultado en la tabla de arriba y en `CLAUDE.md`.
- Las respuestas varían entre corridas: una diferencia de ±1 caso no es significativa.
- Si una métrica cae, **mirar primero el JSON** (`--salida-json`). En esta fase, la mitad de la
  caída inicial era un error de la métrica, no del modelo.

### Pendiente
- **Casos negativos:** preguntas sin respuesta en el corpus. Es la única forma de medir si el
  sistema inventa.
- Casos sobre documentos de embarque reales (Fase 2).

# 01 · Visión y alcance

## El problema

Una operación logística en Centroamérica se apoya en dos tipos de documentos:

1. **Normativa**: el CAUCA (Código Aduanero Uniforme Centroamericano), su Reglamento (RECAUCA),
   convenios regionales, leyes nacionales y manuales internos. Son cientos de artículos. Encontrar
   el que aplica, y saber si es del Código o del Reglamento, lleva tiempo y depende de la
   experiencia de cada persona.
2. **Documentos de cada embarque**: Bill of Lading, Air Waybill, facturas comerciales, packing
   lists y declaraciones aduaneras (DUCA). Muchos llegan escaneados. Sus datos (contenedores,
   pesos, partidas arancelarias, valores) se transcriben a mano y se cruzan a ojo, y ahí aparecen
   los errores que después cuestan multas o demoras.

## La solución

Un asistente que:

- **Responde preguntas sobre la normativa** en lenguaje natural, citando siempre norma y
  artículo, para que la respuesta se pueda verificar. *(Fase 1, hecha.)*
- **Lee los documentos de embarque**, aunque estén escaneados, y **extrae sus datos** en forma
  estructurada. *(Fase 2.)*
- **Cruza los documentos de un mismo embarque** y marca inconsistencias. *(Fase 3.)*

## Usuarios y permisos

| Rol | Qué puede hacer | Caso típico |
|---|---|---|
| **ADMIN** | Todo, incluida la administración de usuarios | Responsable del sistema |
| **OPERADOR** | Cargar documentos, verlos y consultar | Analista de aduanas, coordinador de embarques |
| **LECTOR** | Ver documentos y consultar | Consulta ocasional, auditoría |

Los permisos son `DOCUMENTOS_VER`, `DOCUMENTOS_CARGAR`, `CONSULTAS_REALIZAR` y
`USUARIOS_ADMINISTRAR`. Los resuelve el backend en cada pedido; el frontend solo los usa para
mostrar u ocultar opciones.

## Alcance

### Incluido (hecho)
- Carga de PDF e imágenes (PNG, JPG, TIFF) de hasta 20 MB.
- Extracción de texto: capa de texto nativa del PDF; OCR con Tesseract (español e inglés) solo
  en las páginas escaneadas.
- Fragmentación por artículo en documentos normativos.
- Búsqueda híbrida (semántica + palabras clave) y respuestas citadas.
- Clasificación automática del tipo de documento, corregible a mano.
- Carga masiva de un corpus normativo verificado (CAUCA IV, RECAUCA IV, Convenio).
- Evaluación automática de la calidad de las respuestas.
- Autenticación propia con roles y permisos.

### Incluido (planificado)
- Extracción estructurada de documentos de embarque (Fase 2).
- Validación cruzada de documentos por embarque (Fase 3).
- Despliegue en Railway (backend) y Vercel (frontend).

### Fuera de alcance
- **Asesoría legal vinculante.** El sistema cita la norma, pero no reemplaza el criterio de un
  profesional aduanero. Las respuestas son de apoyo.
- **Transmisión a los sistemas aduaneros** (presentar una DUCA ante el servicio aduanero).
- **Clasificación arancelaria automática** de mercancías (asignar la partida SAC). Se evaluará
  después de la Fase 2.
- **Legislación nacional de cada país** (leyes aduaneras de Guatemala, Honduras, etc.). Por
  ahora solo normativa regional. Se puede sumar con el mismo mecanismo del corpus.
- **Entrenar o ajustar un modelo propio** (fine-tuning). El conocimiento viene de los documentos
  cargados; ver [06 · Decisiones](06-decisiones.md).

## Supuestos y restricciones

- Los textos de las normas se toman de fuentes oficiales públicas (FAOLEX, SIECA). Son las
  **versiones originales de 2008**, sin reformas posteriores (ver
  [07 · Riesgos](07-riesgos-y-pendientes.md)).
- Los documentos cargados, **incluidos los de clientes**, se envían a la API de OpenAI para
  generar embeddings y respuestas. La política de datos de la empresa tiene que permitirlo.
- El texto de Incoterms 2020 tiene derechos de la ICC: solo se carga si la empresa tiene una copia
  con licencia.
- Presupuesto de IA: el costo principal son los embeddings al cargar o reprocesar documentos, y
  cada consulta. Con el corpus actual, reprocesar todo y correr la evaluación cuesta centavos de
  dólar.

## Criterios de éxito del producto

| Criterio | Cómo se mide | Hoy |
|---|---|---|
| Encuentra el artículo que responde | hit@k en el set de evaluación | **100 %** |
| Lo pone primero | MRR | **0,79** |
| Cita norma y artículo | % de casos con todas las citas esperadas | **81 %** |
| No inventa cuando no sabe | casos negativos del set | *pendiente de medir* |
| Extrae bien los campos de un BL | % de campos correctos sobre documentos reales | *Fase 2* |

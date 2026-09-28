# 06 · Registro de decisiones

Cada decisión con su motivo y las alternativas descartadas. Si una decisión cambia, se agrega una
entrada nueva que la reemplaza; no se borra la anterior.

| # | Decisión | Por qué | Alternativas descartadas |
|---|---|---|---|
| D1 | **RAG, no fine-tuning** | Un modelo ajustado no aprende los documentos mejor que el RAG, cuesta más y hay que reentrenarlo cada vez que cambia una norma. Con RAG, cargar una norma nueva la vuelve consultable al instante, y cada respuesta se puede verificar. | Fine-tuning; modelo propio |
| D2 | **pgvector en la misma PostgreSQL** | Una sola base para datos y vectores: transacciones comunes, un solo backup y funciona igual en local y en Railway. El volumen actual (~1.000 fragmentos) está muy lejos de sus límites. | Qdrant u otro vector store aparte |
| D3 | **Archivos originales como `bytea` en PostgreSQL** | El contenedor de Railway es efímero, y así no hace falta un bucket. Límite de 20 MB por archivo. | Volumen de Railway; S3; no guardar el original |
| D4 | **OpenAI** (`text-embedding-3-small`, `gpt-4o-mini`) | Embeddings y chat en un solo proveedor, bajo costo y buen español. Los modelos se configuran por variable de entorno. | Claude API más otro proveedor de embeddings; AWS Bedrock |
| D5 | **Tesseract local**, solo en páginas sin texto | Sin costo por página y sin enviar imágenes afuera. Leer primero la capa de texto nativa es instantáneo y exacto en los PDF digitales. | AWS Textract; Azure Document Intelligence; OCR de todas las páginas |
| D6 | **pypdfium2 para leer y rasterizar PDF** | Parte mucho menos las palabras que pypdf (32 contra 566 en el RECAUCA IV) y no necesita dependencias del sistema (reemplazó a poppler). | pypdf; pdf2image + poppler |
| D7 | **Backend en Docker Compose para desarrollo** | Tesseract no está instalado en Windows; así el entorno local es igual a producción y se evitan los problemas de Windows (event loop, IPv6). | Instalar Tesseract en cada máquina |
| D8 | **Búsqueda híbrida con RRF** | La búsqueda semántica sola dejaba el artículo de la definición fuera del top 5: se perdía entre otros artículos que "hablan de lo mismo". El texto completo lo rescata por las palabras exactas, y RRF combina los dos rankings sin calibrar puntajes. | Solo vectorial; ponderar puntajes a mano |
| D9 | **Palabras clave con OR, no AND** | Con AND, "¿qué es el tránsito aduanero y qué requisitos tiene?" exigía que un fragmento contenga todas las palabras, y la definición no dice "requisitos". Con OR entra, y el ranking premia a los que tienen más palabras. | `websearch_to_tsquery` (AND) |
| D10 | **Fragmentos por artículo en normativa** | La unidad natural de una norma es el artículo: un fragmento que mezcla dos confunde la cita, y conocer el número permite citar "Art. 94". | Ventanas de tamaño fijo para todo |
| D11 | **Corpus curado y verificado página por página** | Una edición que decía "CAUCA IV + RECAUCA" traía normas derogadas, y el sistema las citaba con total seguridad. Para un sistema de consulta legal, una respuesta equivocada pero citada es el peor error posible. | Cargar lo que aparece en internet |
| D12 | **Evaluación automática antes de cada cambio** | Sin medir, "mejoró" es una impresión. La evaluación mostró que la mitad de la caída inicial era un error de la métrica y que un ejemplo en el prompt multiplicaba las citas correctas. | Probar a ojo |
| D13 | **Toma exclusiva + versión de procesamiento** | El worker de la API y el CLI son procesos distintos: sin coordinación, dos procesamientos del mismo documento se pisaban o lo dejaban en error. Una toma condicionada en SQL, más un guardado condicionado a la versión, lo resuelven sin bloqueos largos. | Bloqueos en memoria (no sirven entre procesos) |
| D14 | **Clasificación del tipo con LLM, corregible** | Evita que el usuario tenga que clasificar cada carga. Una edición manual siempre gana, y la intención de clasificar queda guardada en la base para sobrevivir a reinicios. | Tipo obligatorio al cargar |
| D15 | **Revisión cruzada Claude + Codex** | Dos modelos distintos encuentran cosas distintas: en la Fase 1, Codex encontró 8 problemas reales, entre ellos 21 artículos mal numerados que los tests no detectaban. Cada hallazgo se verifica en el código antes de aceptarlo. | Una sola revisión |
| D16 | **Scripts SQL manuales y numerados** | Ningún cambio de esquema se aplica sin una persona que lo revise contra el ambiente. Los scripts son idempotentes y cada uno contiene un solo cambio. | Migraciones automáticas al desplegar |

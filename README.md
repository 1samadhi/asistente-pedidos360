# Asistente de Integración Pedidos360

Evaluación Parcial N°1 — **ISY0101 Ingeniería de Soluciones con IA**

Asistente conversacional que responde las consultas técnicas de los desarrolladores que
integran su comercio a la API de **Pedidos360**. Combina recuperación sobre documentación
(RAG) con consultas en vivo a la API, y decide por sí mismo cuál corresponde en cada caso.

La propuesta de caso completa está en [`propuesta-de-caso.md`](propuesta-de-caso.md).

---

## Qué hace

| Pregunta | Cómo la resuelve |
|---|---|
| *«¿Cómo obtengo un token?»* | Recuperación sobre la documentación interna |
| *«¿Qué significa el claim `aud`?»* | Recuperación sobre fuentes externas (RFC 7519) |
| *«¿Cuántos pedidos llevo?»* | Llamada en vivo a `GET /v1/pedidos` con token de Entra ID |
| *«¿Cómo lo obtengo por API y cuántos llevo?»* | Ambas cosas: documentación + API |

El enrutamiento no está cableado con reglas. Se declaran tres herramientas y el modelo
elige cuál usar, que es lo que distingue a un agente de un RAG plano.

---

## Requisitos

- **Python 3.13** y [uv](https://docs.astral.sh/uv/). Las dependencias están en el
  `pyproject.toml` de este repositorio; `uv sync` instala todo, incluido Python.
- Una **API key de Groq** (gratuita, en [console.groq.com](https://console.groq.com/)).
- *Opcional:* credenciales de Entra ID para las consultas en vivo. **Sin ellas el
  asistente igual funciona**, respondiendo solo con documentación; las herramientas de
  API informan que no están disponibles en vez de inventar datos.

Los embeddings son **locales** (`paraphrase-multilingual-MiniLM-L12-v2`): no requieren
API key y funcionan sin conexión. La primera ejecución descarga ~470 MB y los deja en caché.

---

## Dos formas de usarlo

**`recorrido.ipynb`** — el notebook de demostración. Recorre el sistema pieza por pieza:
el corpus, el troceo, la comparación entre búsqueda densa e híbrida, las herramientas en
vivo, el agente decidiendo, el guardrail y las métricas. No duplica lógica: importa los
módulos de `asistente/`. Funciona en Jupyter local y en Colab, y viene ya ejecutado, así
que se puede leer sin correr nada.

**La línea de comandos** — para usarlo de verdad, y lo que documentan estas instrucciones.

## Puesta en marcha

```bash
# 1. Dependencias
uv sync

# 2. Configuración
cp .env.example .env      # completa las variables (ver abajo)

# 3. Construir el índice vectorial (~30 s la primera vez)
uv run python -m asistente.ingesta

# 4. Preguntar
uv run python -m asistente.agente "¿Cómo obtengo un token para la API?"
uv run python -m asistente.agente "¿Cuántos pedidos lleva mi comercio?"

# Con -v se ve qué herramienta eligió el agente en cada paso
uv run python -m asistente.agente -v "¿Qué scope necesito para crear pedidos?"
```

Todas las variables se leen del `.env` de este directorio.

### Variables de entorno

| Variable | Para qué | Obligatoria |
|---|---|---|
| `GROQ_API_KEY` | Modelo de lenguaje | Sí |
| `PEDIDOS360_URL` | Base de la API | Solo para consultas en vivo |
| `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_APP_ID_URI` | Autenticación | Solo para consultas en vivo |
| `ENTRA_USUARIO_CLIENTE`, `ENTRA_PASSWORD_CLIENTE` | Identidad del comercio | Solo para consultas en vivo |

> **Por qué Entra ID y no el IdP propio de Pedidos360.** Las rutas de negocio del API
> Gateway están enlazadas al autorizador de Entra. Un token emitido por `ms-auth`, aun
> siendo válido y con los *scopes* correctos, recibe **401** en `/v1/pedidos`.

### Sin el laboratorio de AWS

El entorno AWS es un laboratorio académico: la sesión caduca, la instancia se detiene y la
IP pública cambia. Para no depender de él, Pedidos360 se levanta en local y el asistente
cambia a **modo directo**.

```bash
# En el repositorio de Pedidos360
docker compose -f docker-compose.yml -f docker-compose.local.yml \
  up -d --build mysql ms-auth ms-productos ms-pedidos
```

Y en el `.env` de este proyecto:

```bash
PEDIDOS360_MODO="directo"
MS_AUTH_USUARIO="cliente"
MS_AUTH_PASSWORD="..."
```

**Qué cambia entre los dos modos**, que no es solo la URL:

| | `gateway` (AWS) | `directo` (local) |
|---|---|---|
| Rutas | `/v1/pedidos` | `/api/v1/pedidos` |
| Servicios | Un solo host | Un puerto por servicio: 8082, 8081, 9000 |
| Autenticación | Entra ID | IdP propio (`ms-auth`) |

El prefijo `/v1` lo inventa el API Gateway al reenviar: los microservicios exponen
`/api/v1/...`. Y sin gateway no hay autorizador de Entra, así que basta el login del IdP
propio — los Resource Server de Spring aceptan los tres emisores.

> **Estado de esta funcionalidad.** El modo directo está implementado y hay pruebas que
> verifican que cada modo arma las URLs correctas, pero **la ejecución de extremo a extremo
> contra los contenedores no está verificada**: el entorno donde se desarrolló no tenía
> acceso a Docker Hub para construir las imágenes. Si algo falla al levantarlo, es aquí.

---

## Estructura

```
recorrido.ipynb    Notebook de demostración: recorre el sistema paso a paso
corpus/
  interno/     Documentación de Pedidos360 · 10 archivos, 7.210 palabras
               (9 preexistentes + 09-errores-frecuentes.md, escrito en este proyecto)
  externo/     RFC 6749, RFC 7519 y OWASP API Top 10 · 3 archivos, ~4.100 palabras
asistente/
  config.py        Configuración, toda por variables de entorno
  ingesta.py       Troceo por encabezado e índice FAISS
  recuperador.py   Recuperación híbrida: densa + léxica, fusionadas con RRF
  herramientas.py  Consultas en vivo a la API de Pedidos360
  guardrails.py    Redacción de identificadores de infraestructura
  prompts.py       Las tres variantes del prompt de sistema
  agente.py        Agente con tres herramientas
evaluacion/
  preguntas.jsonl        Set de 30 preguntas con fuente y respuesta de referencia
  evaluar.py             Métricas de recuperación y de generación
  comparar_prompts.py    Compara las variantes de prompt
  calibrar_juez.py       Verifica que la rúbrica del juez discrimina
  test_guardrails.py     17 pruebas del filtro de salida
  capturar_evidencia.py  Ejecuta las pruebas y guarda su salida fechada
  auditar_entregable.py  Comprueba el entregable contra la pauta
  evidencias/            Salidas guardadas como evidencia
docs/
  arquitectura.svg                  Diagrama de la solución
  boceto-secuencia-consulta-mixta.svg   Boceto: cómo se resuelve una consulta mixta
presentacion/
  EP1-...pptx            Presentación, generada desde los datos medidos
informe/
  informe-ep1.md         Fuente del informe
  informe-ep1.docx/.pdf  Entregable, generado desde el Markdown
scripts/
  poblar_pedidos.py      Genera pedidos de demostración vía la API
  verificar_api.py       Comprueba la API e imprime un reporte reenviable
  convertir_informe.py   Markdown → .docx y .pdf
  generar_ppt.py         Genera la presentación desde resultados.json
indice/            Índice FAISS y léxico — se genera, no se versiona
```

El corpus externo son **extractos de las secciones pertinentes** de cada fuente, con la
URL del documento completo en la cabecera de cada archivo. Se acota a propósito: incluir
los RFC íntegros (29.000 palabras en inglés) desbalancearía la recuperación frente a las
7.210 palabras de documentación propia en español.

---

## Evaluación

```bash
uv run python -m evaluacion.evaluar                    # recuperación, sin coste
uv run python -m evaluacion.evaluar --generacion --n 30 # + fidelidad y relevancia
```

El set son **30 preguntas** con la fuente esperada y una respuesta de referencia
(`evaluacion/preguntas.jsonl`): 23 sobre documentación propia y 7 sobre fuentes externas.

### Recuperación

Determinista y sin coste, así que corre sobre las 30 preguntas y permite comparar
configuraciones. Resultados actuales:

| Estrategia | Context recall | Context precision | Sin ninguna fuente |
|---|---:|---:|---:|
| Solo semántica | 0,80 | 0,58 | 2 |
| Híbrida 0,5/0,5 | 0,78 | 0,51 | 4 |
| **Híbrida 0,8/0,2 con tope por archivo** | **0,92** | **0,45** | **0** |

La precisión se lee contra su techo: con `k=5` y un tope de dos fragmentos por archivo,
una pregunta con una sola fuente esperada no puede pasar de 2/5. El máximo alcanzable
sobre el set es 0,55, así que 0,45 es el 82% de lo posible.

El camino hasta ahí está documentado en `asistente/recuperador.py`, y no fue recto: la
primera versión híbrida, con pesos iguales y cuota fija por origen, resultó **peor** que
la búsqueda semántica sola (precisión 0,35). La medición es lo que lo detectó.

### Generación

Fidelidad y relevancia se evalúan con un modelo como juez, con una rúbrica de cinco
niveles. Sobre las 30 preguntas: **fidelidad 0,95 · relevancia 0,98**, con 26 respuestas de
fidelidad perfecta y las 30 por encima de 0,75 de relevancia.

`python -m evaluacion.calibrar_juez` verifica que la rúbrica discrimina antes de usarla:
le da cuatro respuestas construidas a propósito —correcta, incompleta, con un dato
inventado y falsa— y exige que las ordene.

> **Medir de más importa.** Sobre una muestra de 8 preguntas la fidelidad daba 1,00. Al
> ampliar a las 30 bajó a 0,88, revelando tres respuestas correctas pero **no
> fundamentadas**: el modelo las sabía de memoria y el contexto recuperado no las
> respaldaba, porque el troceo cortaba las listas de los RFC. Corregido eso, 0,95.

### Otras limitaciones declaradas

- **El set de preguntas lo escribió quien conocía los documentos**, así que comparte
  vocabulario literal con ellos más de lo que lo haría un usuario real preguntando con
  sus palabras. Eso favorece a la búsqueda léxica y probablemente sobreestima el recall.
  Por eso la configuración elegida conserva peso semántico.
- **El *recall* se mide contra una lista de archivos esperados escrita a mano**, que
  también puede equivocarse: una respuesta de referencia afirmaba que el puerto 22 estaba
  cerrado cuando la documentación dice lo contrario, y penalizaba al asistente por
  acertar. Conviene revisar los desacuerdos antes de creerle al set.

## Trazas con LangSmith (opcional)

Registra cada consulta: qué herramienta eligió el modelo, qué fragmentos recuperó, cuánto
tardó y cuántos tokens costó. No hace falta tocar el código — LangChain lo envía solo.

1. Clave gratuita en [smith.langchain.com](https://smith.langchain.com) → *Settings* → *API Keys*.
2. En el `.env`:

```bash
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="lsv2_..."
LANGSMITH_PROJECT="asistente-pedidos360"
```

3. Comprobar y ejecutar:

```bash
uv run python -c "from asistente import config; print(config.estado_trazas())"
uv run python -m asistente.agente "¿Por qué mi token da 401?"
```

Las trazas aparecen en el proyecto `asistente-pedidos360` del panel de LangSmith.

> **Por qué no basta con poner `true`.** Con `LANGSMITH_TRACING="true"` y la clave vacía,
> LangChain intenta enviar cada traza igual y la consola se llena de errores 401 que no son
> un fallo del proyecto. `activar_trazas()` comprueba que haya clave antes de encender, y
> si falta lo dice en vez de fallar en silencio.

## Comprobar que todo cuadra con la pauta

```bash
uv run python -m evaluacion.auditar_entregable   # ¿falta algo que exija la pauta?
uv run python -m evaluacion.capturar_evidencia   # regenera la evidencia fechada
uv run python scripts/convertir_informe.py       # regenera .docx y .pdf
```

La auditoría comprueba que existan los siete elementos de la propuesta y los siete
apartados del informe, que el repositorio contenga lo que la pauta exige —bocetos,
evidencia de pruebas, README—, que las cifras citadas en los documentos coincidan con las
que produce el código, y que no queden marcadores sin completar.

## Seguridad

- El `.env` **no se versiona**: este repositorio es público.
- `guardrails.py` filtra de las respuestas los identificadores de instancia, GUID de
  tenant, IP públicas, tokens y las credenciales de los usuarios de prueba, que aparecen
  legítimamente en el corpus pero no deben llegar al usuario final.
- El asistente **no modifica** Pedidos360: lo consume como cualquier comercio integrado.

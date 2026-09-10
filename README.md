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

- **Python 3.13** y [uv](https://docs.astral.sh/uv/) — las dependencias son las del curso,
  declaradas en el `pyproject.toml` de la raíz del repositorio.
- Una **API key de Groq** (gratuita, en [console.groq.com](https://console.groq.com/)).
- *Opcional:* credenciales de Entra ID para las consultas en vivo. **Sin ellas el
  asistente igual funciona**, respondiendo solo con documentación; las herramientas de
  API informan que no están disponibles en vez de inventar datos.

Los embeddings son **locales** (`paraphrase-multilingual-MiniLM-L12-v2`): no requieren
API key y funcionan sin conexión. La primera ejecución descarga ~470 MB y los deja en caché.

---

## Puesta en marcha

```bash
# 1. Dependencias, desde la raíz del repositorio
uv sync

# 2. Configuración
cd EP1-asistente-pedidos360
cp .env.example .env      # completa las variables (ver abajo)

# 3. Construir el índice vectorial (~30 s la primera vez)
uv run --project .. python -m asistente.ingesta

# 4. Preguntar
uv run --project .. python -m asistente.agente "¿Cómo obtengo un token para la API?"
uv run --project .. python -m asistente.agente "¿Cuántos pedidos lleva mi comercio?"

# Con -v se ve qué herramienta eligió el agente en cada paso
uv run --project .. python -m asistente.agente -v "¿Qué scope necesito para crear pedidos?"
```

`GROQ_API_KEY` se toma del `.env` de la raíz del repositorio si ya lo tienes configurado
para el curso; no hace falta duplicarla.

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

El entorno AWS es un laboratorio académico y su IP pública cambia en cada reinicio. Para
trabajar sin depender de él, se levanta Pedidos360 en local y se apunta `PEDIDOS360_URL`
a `http://localhost:8082`:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build -d
```

---

## Estructura

```
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
  preguntas.jsonl      Set de 30 preguntas con fuente y respuesta de referencia
  evaluar.py           Métricas de recuperación y de generación
  comparar_prompts.py  Compara las variantes de prompt
  calibrar_juez.py     Verifica que la rúbrica del juez discrimina
  test_guardrails.py   17 pruebas del filtro de salida
  evidencias/          Salidas guardadas como evidencia
docs/
  arquitectura.svg     Diagrama de la solución
scripts/
  poblar_pedidos.py    Genera pedidos de demostración vía la API
  verificar_api.py     Comprueba la API e imprime un reporte reenviable
indice/          Índice FAISS y léxico — se genera, no se versiona
```

El corpus externo son **extractos de las secciones pertinentes** de cada fuente, con la
URL del documento completo en la cabecera de cada archivo. Se acota a propósito: incluir
los RFC íntegros (29.000 palabras en inglés) desbalancearía la recuperación frente a las
7.210 palabras de documentación propia en español.

---

## Evaluación

```bash
uv run --project .. python -m evaluacion.evaluar                    # recuperación, sin coste
uv run --project .. python -m evaluacion.evaluar --generacion --n 8 # + fidelidad y relevancia
```

El set son **30 preguntas** con la fuente esperada y una respuesta de referencia
(`evaluacion/preguntas.jsonl`): 23 sobre documentación propia y 7 sobre fuentes externas.

### Recuperación

Determinista y sin coste, así que corre sobre las 30 preguntas y permite comparar
configuraciones. Resultados actuales:

| Estrategia | Context recall | Context precision | Sin ninguna fuente |
|---|---:|---:|---:|
| Solo semántica | 0,77 | 0,58 | 4 |
| Léxica sola | 0,87 | 0,53 | 2 |
| Híbrida 0,5/0,5 | 0,78 | 0,51 | 4 |
| **Híbrida 0,8/0,2** (elegida) | **0,85** | **0,61** | **3** |

El camino hasta ahí está documentado en `asistente/recuperador.py`, y no fue recto: la
primera versión híbrida, con pesos iguales y cuota fija por origen, resultó **peor** que
la búsqueda semántica sola (precisión 0,35). La medición es lo que lo detectó.

### Generación

Fidelidad y relevancia se evalúan con un modelo como juez, lo que consume cuota, así que
corren sobre una submuestra. Sobre 8 preguntas: **fidelidad 1,00 · relevancia 1,00**.

> **Limitación del método.** El juez devuelve 0 o 1 y no valores intermedios —verificado
> dándole respuestas deliberadamente incorrectas, que puntúa 0—, así que discrimina entre
> respuesta buena y mala pero no gradúa la calidad. Un 1,00 con esta métrica significa
> «ninguna respuesta de la muestra fue incorrecta», no «no hay nada que mejorar».

### Otras limitaciones declaradas

- **El set de preguntas lo escribió quien conocía los documentos**, así que comparte
  vocabulario literal con ellos más de lo que lo haría un usuario real preguntando con
  sus palabras. Eso favorece a la búsqueda léxica y probablemente sobreestima el recall.
  Por eso la configuración elegida conserva peso semántico.
- **El *recall* se mide contra una lista de archivos esperados escrita a mano.** Cuando la
  respuesta aparece legítimamente en otro documento, se cuenta como fallo aunque el
  asistente responda bien: es lo que ocurre con la pregunta 16.

## Seguridad

- El `.env` **no se versiona**: este repositorio es público.
- `guardrails.py` filtra de las respuestas los identificadores de instancia, GUID de
  tenant, IP públicas, tokens y las credenciales de los usuarios de prueba, que aparecen
  legítimamente en el corpus pero no deben llegar al usuario final.
- El asistente **no modifica** Pedidos360: lo consume como cualquier comercio integrado.

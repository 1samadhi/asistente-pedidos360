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
  interno/     Documentación propia de Pedidos360 · 9 archivos, 6.334 palabras
  externo/     RFC 6749, RFC 7519 y OWASP API Top 10 · 3 archivos, ~4.100 palabras
asistente/
  config.py        Configuración, toda por variables de entorno
  ingesta.py       Troceo del corpus e índice FAISS
  recuperador.py   Recuperación con cuota por origen
  herramientas.py  Consultas en vivo a la API de Pedidos360
  guardrails.py    Redacción de identificadores de infraestructura
  agente.py        Agente con tres herramientas
scripts/
  poblar_pedidos.py   Genera pedidos de demostración vía la API
indice/          Índice FAISS — se genera, no se versiona
```

El corpus externo son **extractos de las secciones pertinentes** de cada fuente, con la
URL del documento completo en la cabecera de cada archivo. Se acota a propósito: incluir
los RFC íntegros (29.000 palabras en inglés) desbalancearía la recuperación frente a las
6.334 palabras de documentación propia en español.

---

## Estado actual

El pipeline funciona de extremo a extremo y el enrutamiento entre documentación y API en
vivo es correcto. **Las respuestas todavía tienen defectos medidos y pendientes de
corregir**, documentados aquí porque la evaluación del sistema es parte del encargo:

1. **Recuperación insuficiente en preguntas de soporte.** Una consulta como *«mi token es
   válido pero da 401»* no recupera el fragmento de `03-api-gateway.md` que contiene la
   respuesta: la pregunta usa el vocabulario de quien sufre el problema («401», «token
   válido») y el documento el de quien lo diseñó («autorizador», «emisor»). El modelo
   responde con lo que recibe, y produce una explicación plausible pero incorrecta.
2. **Errores de ordenamiento.** Al pedir «qué producto factura más», el modelo lee mal el
   máximo sobre una lista ordenada por otro criterio.
3. **Respuestas parciales en preguntas mixtas.** Contesta la mitad que requiere la API y
   omite la mitad documental.

Correcciones en curso: encabezado de sección en cada fragmento antes de vectorizar,
recuperación híbrida BM25 + densa, y ranking calculado en la herramienta en vez de
delegado al modelo.

---

## Seguridad

- El `.env` **no se versiona**: este repositorio es público.
- `guardrails.py` filtra de las respuestas los identificadores de instancia, GUID de
  tenant, IP públicas, tokens y las credenciales de los usuarios de prueba, que aparecen
  legítimamente en el corpus pero no deben llegar al usuario final.
- El asistente **no modifica** Pedidos360: lo consume como cualquier comercio integrado.

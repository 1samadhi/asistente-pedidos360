# Propuesta de caso organizacional

**Evaluación Parcial N°1 — ISY0101 Ingeniería de Soluciones con IA**
Asistente de integración para Pedidos360

| | |
|---|---|
| **Equipo** | Ismael Oyarzún (isma.oyarzun@duocuc.cl) + *[completar compañero/a]* |
| **Fecha** | Septiembre 2026 |
| **Indicadores** | IL1.1, IL1.2, IL1.3, IL1.4 |

> **Nota de transparencia.** La organización descrita es un encuadre plausible sobre un
> sistema **real, construido y desplegado por el equipo** en la asignatura de Cloud
> (Experiencia 1). La infraestructura, la documentación y los datos que se citan en este
> documento existen y fueron verificados; lo que se propone como ficción razonable es la
> figura de la empresa que comercializa ese sistema. El uso del proyecto como base fue
> consultado y autorizado por el docente.

---

## 1. Nombre y breve descripción de la organización

**Pedidos360** es una PYME tecnológica chilena que ofrece a comercios asociados una
plataforma B2B de gestión de pedidos entregada como API. Su propuesta de valor
diferenciadora es la **autenticación federada**: cada comercio que se adhiere puede
acceder con el Microsoft Entra ID corporativo que ya usa internamente, sin crear ni
administrar usuarios nuevos en la plataforma.

**Rubro:** software B2B / integración de sistemas.
**Tamaño:** pequeña (equipo de ingeniería reducido, sin área de soporte dedicada).

La plataforma está operativa y consta de tres microservicios Spring Boot (Java 21):

| Servicio | Rol |
|---|---|
| `ms-auth` | Identity Provider OIDC propio, firma RS256 |
| `ms-productos` | Catálogo — Resource Server |
| `ms-pedidos` | Gestión de pedidos — Resource Server |

Desplegados sobre **AWS EC2 + API Gateway (HTTP API) + RDS MySQL**, con un frontend
Angular. Los Resource Server aceptan simultáneamente tokens de **tres emisores**
—el IdP propio, Amazon Cognito y Microsoft Entra ID— resueltos por el claim `iss`.

---

## 2. Identificación y descripción del problema

**El onboarding técnico de cada comercio nuevo consume horas de ingeniería.**

Adherirse a Pedidos360 no es copiar una API key. El desarrollador del comercio debe
entender qué emisor de identidad le corresponde, cómo obtener un token, qué *scopes*
necesita, cómo se propaga la identidad entre servicios y qué significa cada error. Esa
información hoy está repartida entre un README, seis documentos técnicos, un CHANGELOG,
dos colecciones de API y el código fuente.

**Evidencia concreta del problema, verificada en el sistema en producción:**

Un token emitido por el propio `ms-auth` de Pedidos360 —con el `iss` correcto, la
audiencia correcta y los *scopes* `pedidos.leer pedidos.escribir`— recibe **HTTP 401** al
llamar `GET /v1/pedidos`. La causa es que esa ruta está enlazada al autorizador de
**Entra ID**, mientras el autorizador del IdP propio solo cubre `/auth/userinfo`. Un
desarrollador que se integra no tiene forma razonable de deducirlo: la respuesta exige
cruzar la documentación de autenticación con la configuración real del API Gateway.

Ese es exactamente el tipo de consulta que hoy termina en el equipo de ingeniería.

**Impacto actual:**

- Horas de ingeniería desviadas a responder preguntas repetidas de integración.
- Fricción en la adhesión de comercios nuevos: el tiempo de integración es un costo
  visible para el cliente y un obstáculo comercial.
- Conocimiento concentrado en las personas que construyeron el sistema.

---

## 3. Objetivos de la intervención

**Objetivo general.** Implementar un asistente conversacional que responda de forma
autónoma las consultas técnicas de los desarrolladores que integran sus comercios a
Pedidos360, fundamentando cada respuesta en la documentación oficial y en el estado real
del sistema.

**Objetivos específicos y medibles:**

| # | Objetivo | Métrica | Meta |
|---|---|---|---|
| O1 | Cubrir las consultas frecuentes de integración | % de un set de 30 preguntas respondidas sin intervención humana | ≥ 85% |
| O2 | Asegurar que las respuestas se apoyen en las fuentes | *Faithfulness* (fidelidad al contexto recuperado) | ≥ 0,80 |
| O3 | Asegurar que las respuestas sean útiles | *Answer relevancy* | ≥ 0,80 |
| O4 | Recuperar el contexto correcto | *Context precision* / *context recall* | ≥ 0,70 |
| O5 | Responder también sobre datos operativos actuales | Consultas de estado resueltas contra la API en vivo | ≥ 90% |
| O6 | No filtrar información sensible | Identificadores de infraestructura en las respuestas | 0 |

---

## 4. Datos disponibles

### 4.1 Fuentes internas — documentación propia (existente y verificada)

| Documento | Palabras | Contenido |
|---|---:|---|
| `README.md` | 1.236 | Arquitectura, endpoints, emisores, decisiones de diseño |
| `docs/02-entra-id.md` | 945 | Configuración del tenant y de las apps |
| `CHANGELOG.md` | 810 | Evolución y versionado de la API |
| `docs/03-api-gateway.md` | 758 | Rutas, autorizadores, integraciones |
| `docs/05-base-de-datos.md` | 637 | Modelo de datos y RDS |
| `docs/04-despliegue-ec2.md` | 580 | Despliegue y operación |
| `docs/06-frontend-angular.md` | 552 | Integración del frontend con MSAL |
| `front-angular/README.md` | 479 | Configuración del cliente |
| `docs/01-cognito.md` | 337 | Identity as a Service |
| **Total** | **≈ 6.334** | |

Se suman como fuentes internas los **contratos de API** (colecciones Postman y Thunder
Client) y el **código fuente Java** de los tres microservicios, del que se extraen los
*scopes* exigidos por cada endpoint.

### 4.2 Fuentes internas — datos operativos en vivo

Consultables vía API autenticada, verificados al momento de escribir esta propuesta:

- **Catálogo:** 4 productos con nombre y precio.
- **Pedidos:** 86 registros de demostración, repartidos en 2 comercios (56 y 30),
  con 129 unidades y $6.156.710 en el comercio principal.

### 4.3 Fuentes externas

- **RFC 6749** (OAuth 2.0) y **RFC 7519** (JSON Web Token).
- Documentación oficial de **Microsoft Entra ID**, **AWS API Gateway** y **Spring Security**.
- **OWASP API Security Top 10**.
- **Ley 19.628** sobre protección de la vida privada.

---

## 5. Restricciones y requerimientos particulares

**Normativas y de privacidad**

- **Ley 19.628.** La tabla `pedidos` asocia cada registro al identificador del sujeto
  autenticado. El asistente debe operar sobre datos del comercio consultante y no
  exponer información de otros.
- **Aislamiento por identidad.** El endpoint filtra por el `sub` del token; el asistente
  debe propagar la identidad del solicitante y nunca consultar con un token privilegiado
  en nombre de un tercero.

**De seguridad del propio asistente**

- El corpus interno contiene identificadores de infraestructura (ID de instancia EC2,
  tenant de Entra ID, endpoints internos, credenciales de usuarios de prueba). El sistema
  debe incorporar un guardrail que impida su aparición en las respuestas.

**Técnicas y de plataforma**

- **Cuota del proveedor de LLM.** Groq, capa gratuita: 200.000 tokens diarios. Obliga a
  usar el modelo rápido en tareas de alto volumen y a acotar el tamaño del contexto.
- **Sin endpoint de embeddings.** El proveedor no ofrece embeddings, por lo que se usa un
  modelo multilingüe local (`paraphrase-multilingual-MiniLM-L12-v2`), sin costo y offline.
- **Infraestructura efímera.** El entorno AWS es un laboratorio académico: la IP pública
  cambia en cada reinicio. La URL de la API se parametriza por variable de entorno y se
  dispone de un despliegue local equivalente vía Docker Compose como alternativa.
- **Limitación conocida de los datos.** La API fija la fecha de creación del pedido en el
  instante de la petición y no admite datos retroactivos, por lo que los pedidos de
  demostración comparten marca temporal. Esto acota el análisis de series de tiempo.

**De alcance**

- El asistente **no modifica** Pedidos360. Lo consume como cualquier comercio integrado,
  autenticándose por el mismo mecanismo OAuth 2.0.

---

## 6. Motivación para el uso de agentes de IA, LLMs y RAG

> **Esta sección la redacta el equipo.** La pauta prohíbe expresamente el uso de IA para
> escribir justificaciones técnicas. A continuación quedan ordenados los hechos
> verificados y las preguntas que la justificación debe responder, para que el equipo
> construya el argumento con sus propias palabras.

**Hechos disponibles para argumentar:**

- El conocimiento está disperso en ~6.300 palabras de documentación, código y contratos.
- Existen preguntas cuya respuesta **no está escrita en ningún documento** y requieren
  cruzar dos fuentes (el caso del 401 documentado en el punto 2).
- Existen preguntas que **no se pueden responder con documentos**, porque dependen del
  estado actual del sistema (cuántos pedidos, qué producto se pide más).
- La documentación cambia con cada versión; un modelo sin acceso a fuentes quedaría
  desactualizado y no podría citar en qué se basa.

**Preguntas que la justificación debe responder:**

1. ¿Por qué RAG y no un LLM respondiendo de memoria? (pensar en trazabilidad, en poder
   citar la fuente y en el costo de una respuesta inventada sobre autenticación)
2. ¿Por qué hace falta un agente con herramientas y no solo recuperación documental?
3. ¿Por qué combinar fuentes internas y externas en vez de usar solo las propias?
4. ¿Qué gana la organización que no ganaría con un buscador o un FAQ estático?

---

## 7. Referencias y anexos

**Repositorios del sistema base**

- Microservicios: `https://github.com/1samadhi/cloud-exp1-oidc`
- Frontend: `https://github.com/1samadhi/cloud-exp1-front-angular`
- *[Pendiente]* Repositorio del asistente (entregable de esta evaluación).

**Sistema en operación**

- API Gateway (stage `desarrollo`):
  `https://j37oj1wn16.execute-api.us-east-1.amazonaws.com/desarrollo`

**Documentos del curso**

- Pauta EP1 — ISY0101, Subdirección de Diseño Instruccional.
- Materiales RA1: IL1.1 a IL1.4.

**Normativa y estándares**

- Ley 19.628 sobre Protección de la Vida Privada.
- RFC 6749 — *The OAuth 2.0 Authorization Framework*.
- RFC 7519 — *JSON Web Token (JWT)*.
- OWASP API Security Top 10.

---

## Declaración de uso de Inteligencia Artificial

> *[Ajustar por el equipo antes de entregar, según lo que efectivamente se use.]*

En la elaboración de este proyecto se utilizó **Claude (Anthropic)** como herramienta de
apoyo para: análisis de la pauta de evaluación, exploración e inventario de la
documentación existente, generación del script de poblamiento de datos de demostración,
estructuración de este documento y elaboración de diagramas.

**No se utilizó IA** para la redacción de la justificación de decisiones técnicas
(sección 6), las conclusiones ni las reflexiones individuales, conforme a las
indicaciones de la pauta. Todo contenido generado con apoyo de IA fue revisado y
validado por el equipo.

Referencia de citación: https://bibliotecas.duoc.cl/ia

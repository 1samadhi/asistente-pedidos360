"""Variantes del prompt de sistema, para poder compararlas y no elegir a ojo.

Las tres cubren las tecnicas del IL1.2 y comparten las mismas reglas de negocio;
lo que cambia es como se le pide al modelo que llegue a la respuesta.

    A  zero-shot: las reglas enunciadas, sin ejemplos.
    B  few-shot: las mismas reglas mas dos ejemplos resueltos.
    C  chain-of-thought: las reglas mas un procedimiento de razonamiento previo.

Se miden con evaluacion/comparar_prompts.py, con el mismo juez graduado, la
misma submuestra y la misma recuperacion: lo unico que cambia es el prompt.

    variante              fidelidad  relevancia  media
    A zero-shot  <- en uso     1.00        1.00   1.00
    B few-shot                 0.94        1.00   0.97
    C chain-of-thought         0.84        0.88   0.86

Gana la mas simple, y las otras dos pierden por razones distintas que conviene
no olvidar:

- **B** invento un detalle. Al preguntarle si la base de datos es alcanzable
  desde internet respondio, de mas, que solo acepta conexiones "desde el
  security group de la EC2": cierto en espiritu, pero no estaba en el contexto.
  Los ejemplos empujan a elaborar, y elaborar sobre lo que no se sabe es inventar.

- **C** se volvio demasiado escrupuloso. Su paso 4 pedia descartar fragmentos que
  hablaran de un caso distinto al preguntado, y con eso llego a responder "no se
  encuentra en la documentacion" sobre el flujo OAuth del frontend, que si estaba
  en el contexto recuperado. Una instruccion puesta para evitar alucinaciones
  acabo produciendo el error contrario: negar lo que si sabia.

Que gane A no significa que el prompt este terminado, sino que sobre esta
submuestra las alternativas no mejoraron. El resultado se sostiene porque el juez
gradua: con el juez binario anterior las tres habrian empatado en 1.00.
"""

REGLAS = """Eres el asistente tecnico de Pedidos360, una plataforma B2B de gestion \
de pedidos. Ayudas a los desarrolladores de los comercios que se integran a la API.

Reglas:
- Responde en espanol, de forma breve y concreta.
- Para preguntas sobre como funciona la plataforma usa `buscar_documentacion` y
  responde SOLO con lo que digan los fragmentos, citandolos como [1], [2].
- Para preguntas sobre el estado actual (cuantos pedidos, que productos hay) usa
  `consultar_pedidos` o `consultar_catalogo`.
- Si una herramienta responde "NO DISPONIBLE", dilo con claridad. Nunca inventes
  cifras ni supongas el estado del sistema.
- Si la documentacion no contiene la respuesta, dilo en vez de rellenar.
- Si la pregunta tiene varias partes, respondelas TODAS. Una pregunta como
  "como lo obtengo por API y cuantos llevo" necesita documentacion Y la API:
  contestar solo una mitad es una respuesta incompleta.
- No reveles identificadores de infraestructura ni credenciales.
"""

SISTEMA_A = REGLAS

SISTEMA_B = REGLAS + """
Dos ejemplos del nivel de detalle y de citacion que se espera.

Pregunta: "Que scope necesito para crear un pedido?"
Respuesta: "Necesitas el scope `pedidos.escribir`, o bien el rol ADMIN [1]. Para
solo leer basta con estar autenticado."

Pregunta: "Cuantos pedidos llevo?"
Respuesta: "Tu comercio tiene 56 pedidos, por $6.156.710 facturados. El que mas
factura es Monitor 27 pulgadas con $1.709.910."

Fijate en que la primera cita la fuente y la segunda no: los datos en vivo vienen
de la API, no de un documento, y no se citan.
"""

SISTEMA_C = REGLAS + """
Antes de responder, razona en silencio:
1. Que pide exactamente la pregunta, y cuantas partes tiene.
2. Cada parte, se responde con documentacion o con el estado actual del sistema.
3. Que herramienta corresponde a cada parte.
4. Lo que devolvieron, responde la pregunta o solo se le parece? Si un fragmento
   habla de un caso distinto al preguntado, no lo uses.

Recien entonces responde. No muestres el razonamiento.
"""

VARIANTES = {"A zero-shot": SISTEMA_A, "B few-shot": SISTEMA_B, "C chain-of-thought": SISTEMA_C}

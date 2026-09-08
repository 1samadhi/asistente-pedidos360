"""El asistente: decide entre documentacion y datos en vivo, y responde citando.

El enrutamiento no esta cableado con reglas: se declaran tres herramientas y el
modelo elige. "Como obtengo un token" se responde con documentacion; "cuantos
pedidos llevo" exige llamar la API; "como saco el reporte y cuantos llevo" pide
las dos, y ese caso mixto es el que justifica un agente en lugar de un RAG plano.
"""
# langchain 1.x movio el ejecutor clasico a langchain_classic; es la convencion
# que usa el resto del curso (ver RA2/IL2.1 y RA2/IL2.2).
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from asistente import config, guardrails, herramientas
from asistente.recuperador import cargar_indice, formatear_contexto, recuperar_mixto

SISTEMA = """Eres el asistente tecnico de Pedidos360, una plataforma B2B de gestion \
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
- No reveles identificadores de infraestructura ni credenciales.
"""

_almacen = None


@tool
def buscar_documentacion(consulta: str) -> str:
    """Busca en la documentacion de Pedidos360 y en las fuentes externas (RFC de
    OAuth 2.0 y JWT, OWASP). Uselo para preguntas sobre como funciona la API,
    autenticacion, endpoints, despliegue o decisiones de diseno."""
    global _almacen
    if _almacen is None:
        _almacen = cargar_indice()
    return formatear_contexto(recuperar_mixto(consulta, almacen=_almacen))


@tool
def consultar_pedidos() -> str:
    """Consulta en vivo los pedidos del comercio autenticado: cuantos hay, de que
    productos y por que monto. Uselo para preguntas sobre el estado actual."""
    return herramientas.consultar_pedidos()


@tool
def consultar_catalogo() -> str:
    """Consulta en vivo el catalogo de productos con sus precios actuales."""
    return herramientas.consultar_catalogo()


HERRAMIENTAS = [buscar_documentacion, consultar_pedidos, consultar_catalogo]


def crear_agente(verboso: bool = False) -> AgentExecutor:
    llm = ChatGroq(model=config.MODELO, temperature=0.1, reasoning_effort="low")
    prompt = ChatPromptTemplate.from_messages([
        ("system", SISTEMA),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agente = create_tool_calling_agent(llm, HERRAMIENTAS, prompt)
    return AgentExecutor(agent=agente, tools=HERRAMIENTAS, verbose=verboso,
                         max_iterations=5, handle_parsing_errors=True)


def preguntar(pregunta: str, ejecutor: AgentExecutor | None = None) -> str:
    ejecutor = ejecutor or crear_agente()
    salida = ejecutor.invoke({"input": pregunta})["output"]
    saneada, reemplazos = guardrails.sanear(salida)
    if reemplazos:
        saneada += f"\n\n_({len(reemplazos)} dato(s) interno(s) omitido(s) por politica.)_"
    return saneada


if __name__ == "__main__":
    import sys
    ejecutor = crear_agente(verboso="-v" in sys.argv)
    consulta = " ".join(a for a in sys.argv[1:] if a != "-v")
    print(preguntar(consulta or "Como obtengo un token para llamar la API?", ejecutor))

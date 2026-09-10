"""Configuracion central del asistente.

Todo lo que cambia entre entornos vive aqui y se lee del entorno, para que
pasar de la API local a la desplegada en AWS no toque una linea de codigo.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# --- Modelos (ver CLAUDE.md del curso) ---
MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MODELO_RAPIDO = os.getenv("GROQ_MODEL_FAST", "openai/gpt-oss-20b")
MODELO_EMBEDDINGS = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# --- Corpus e indice ---
CORPUS = RAIZ / "corpus"
INDICE = RAIZ / "indice"
TAMANO_CHUNK = int(os.getenv("TAMANO_CHUNK", "900"))
SOLAPE_CHUNK = int(os.getenv("SOLAPE_CHUNK", "150"))
# Los RFC son texto plano con listas indentadas largas y sin encabezados internos:
# con 900 caracteres se parten las definiciones de error a mitad de frase, y el
# fragmento llega al modelo sin el termino que define. Se les da mas aire.
TAMANO_CHUNK_EXTERNO = int(os.getenv("TAMANO_CHUNK_EXTERNO", "1600"))
K_RECUPERACION = int(os.getenv("K_RECUPERACION", "5"))

# --- API de Pedidos360 ---
# Dos modos, porque la API se ve distinta segun por donde se entre:
#
#   gateway  (por defecto)  AWS API Gateway unifica los microservicios en un solo
#                           host y publica las rutas como /v1/...
#   directo                 Sin gateway: cada microservicio en su propio puerto y
#                           con su prefijo real /api/v1/... Es lo que hay al
#                           levantar Pedidos360 en local con Docker, y sirve para
#                           trabajar sin depender del laboratorio de AWS.
MODO_API = os.getenv("PEDIDOS360_MODO", "gateway").lower()

if MODO_API == "directo":
    PREFIJO = "/api/v1"
    URL_PEDIDOS = os.getenv("PEDIDOS360_PEDIDOS_URL", "http://localhost:8082").rstrip("/")
    URL_PRODUCTOS = os.getenv("PEDIDOS360_PRODUCTOS_URL", "http://localhost:8081").rstrip("/")
    URL_AUTH = os.getenv("PEDIDOS360_AUTH_URL", "http://localhost:9000").rstrip("/")
else:
    PREFIJO = "/v1"
    _base = os.getenv(
        "PEDIDOS360_URL",
        "https://j37oj1wn16.execute-api.us-east-1.amazonaws.com/desarrollo",
    ).rstrip("/")
    URL_PEDIDOS = URL_PRODUCTOS = URL_AUTH = _base

PEDIDOS360_URL = URL_PEDIDOS  # compatibilidad con los scripts existentes

# Credenciales del IdP propio, para el modo directo. Los Resource Server de
# Spring aceptan los tres emisores, asi que sin el gateway de por medio basta con
# el login de ms-auth y no hace falta Entra ID.
MS_AUTH_USUARIO = os.getenv("MS_AUTH_USUARIO", "cliente")
MS_AUTH_PASSWORD = os.getenv("MS_AUTH_PASSWORD", "")

# Credenciales de Entra ID: en modo gateway, las rutas de negocio estan enlazadas
# al autorizador de Entra, no al del IdP propio.
# --- LangSmith: trazas de cada ejecucion (opcional) ---
# LangChain envia las trazas solo, leyendo estas variables. No hace falta tocar
# el codigo del agente.
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "asistente-pedidos360")


def activar_trazas() -> bool:
    """Enciende LangSmith solo si hay clave, y devuelve si quedo activo.

    Poner LANGSMITH_TRACING=true con la clave vacia no es inocuo: LangChain
    intenta enviar cada traza igual y la consola se llena de errores 401 que no
    son un fallo del proyecto. Se comprueba antes de encender.
    """
    quiere = os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes")
    clave = os.getenv("LANGSMITH_API_KEY", "").strip()
    activo = quiere and bool(clave)
    os.environ["LANGSMITH_TRACING"] = "true" if activo else "false"
    if activo:
        os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
    return activo


def estado_trazas() -> str:
    """Texto para explicar por que las trazas estan o no activas."""
    quiere = os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes")
    clave = bool(os.getenv("LANGSMITH_API_KEY", "").strip())
    if quiere and clave:
        return f"activas · proyecto '{LANGSMITH_PROJECT}'"
    if quiere and not clave:
        return "pedidas pero sin LANGSMITH_API_KEY: se dejan apagadas"
    return "apagadas (LANGSMITH_TRACING no esta en true)"


def hay_credenciales_api() -> bool:
    """Sin credenciales el asistente sigue respondiendo, pero solo con documentos."""
    if MODO_API == "directo":
        return bool(MS_AUTH_PASSWORD)
    return all([ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_APP_ID_URI,
                ENTRA_USUARIO, ENTRA_PASSWORD])

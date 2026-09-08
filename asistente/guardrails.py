"""Filtro de salida: impide que identificadores de infraestructura lleguen al usuario.

El corpus interno es documentacion de operacion y contiene datos que un comercio
integrado no tiene por que ver: identificadores de instancia, el tenant de Entra,
IPs de la maquina y las credenciales de los usuarios de prueba del IdP. El
recuperador puede traer un fragmento que los incluya de forma legitima; lo que no
puede pasar es que aparezcan en la respuesta.
"""
import re

PATRONES = [
    (re.compile(r"\bi-[0-9a-f]{8,17}\b"), "[id-de-instancia]"),
    (re.compile(r"\bvpc-[0-9a-f]{8,17}\b"), "[id-de-vpc]"),
    (re.compile(r"\bsubnet-[0-9a-f]{8,17}\b"), "[id-de-subred]"),
    (re.compile(r"\bsg-[0-9a-f]{8,17}\b"), "[grupo-de-seguridad]"),
    # GUID: cubre tenant y client id de Entra
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
                re.I), "[identificador-interno]"),
    # IPv4 publica (se dejan pasar las privadas y localhost, que son inocuas)
    (re.compile(r"\b(?!10\.|127\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)"
                r"(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip-del-servidor]"),
    (re.compile(r"\b(?:admin|cliente)123\b"), "[credencial-omitida]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"),
     "[token-omitido]"),
    (re.compile(r"\bgsk_[A-Za-z0-9]{10,}\b"), "[clave-omitida]"),
]


def sanear(texto: str) -> tuple[str, list[str]]:
    """Devuelve (texto saneado, lista de reemplazos aplicados)."""
    aplicados = []
    for patron, reemplazo in PATRONES:
        texto, n = patron.subn(reemplazo, texto)
        if n:
            aplicados.extend([reemplazo] * n)
    return texto, aplicados

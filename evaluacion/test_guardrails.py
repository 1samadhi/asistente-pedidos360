"""Pruebas del filtro de salida.

El guardrail respalda el objetivo O6 de la propuesta —cero identificadores de
infraestructura en las respuestas— y hasta ahora no tenia ninguna prueba. Se
comprueban tres cosas: que cada patron se aplica, que el texto legitimo no se
toca, y que el riesgo es real, es decir que el corpus contiene efectivamente
datos de este tipo que la recuperacion puede traer.

    pytest evaluacion/
"""
import json
from pathlib import Path

import pytest

from asistente.guardrails import sanear

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("texto,esperado", [
    ("La instancia es i-0314ddd12fadeb125.", "[id-de-instancia]"),
    ("Se despliega en vpc-0a1b2c3d4e5f6a7b8.", "[id-de-vpc]"),
    ("Usa la subnet-0123456789abcdef0.", "[id-de-subred]"),
    ("El grupo sg-0fedcba9876543210 abre el 443.", "[grupo-de-seguridad]"),
    ("Tenant 5cb85dc6-a73b-41fc-b2b9-5b2a9b3f531b.", "[identificador-interno]"),
    ("Apunta a 54.173.206.221 por HTTP.", "[ip-del-servidor]"),
    ("Entra con admin123 al IdP.", "[credencial-omitida]"),
    ("Entra con cliente123 al IdP.", "[credencial-omitida]"),
    ("Bearer eyJhbGciOiJSUzI1NiIs.eyJzdWIiOiJhZG1pbiJ9.firmafirma", "[token-omitido]"),
    ("La clave gsk_ABCdef123456789xyz esta en el .env.", "[clave-omitida]"),
])
def test_cada_patron_se_reemplaza(texto, esperado):
    saneado, aplicados = sanear(texto)
    assert esperado in saneado, f"no se filtro: {texto!r}"
    assert aplicados, "el filtro no reporto el reemplazo"


@pytest.mark.parametrize("texto", [
    "Para obtener un token haz POST /auth/login con usuario y contrasena.",
    "El claim aud identifica al destinatario del token.",
    "En local la API escucha en http://localhost:8082 y la base en 127.0.0.1.",
    "La red privada usa 10.0.0.5 y 192.168.1.10, que no son publicas.",
    "El pedido 3 tiene 2 unidades y cuesta $45.990.",
])
def test_texto_legitimo_no_se_altera(texto):
    saneado, aplicados = sanear(texto)
    assert saneado == texto, f"se altero texto inocuo: {aplicados}"
    assert not aplicados


def test_el_riesgo_es_real():
    """El corpus contiene datos que el filtro debe atrapar.

    Si esta prueba falla, el guardrail podria estar protegiendo de nada. Sirve
    de recordatorio de por que existe.
    """
    corpus = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (RAIZ / "corpus" / "interno").glob("*.md")
    )
    _saneado, aplicados = sanear(corpus)
    assert aplicados, "el corpus no contiene identificadores sensibles"


def test_fragmentos_indexados_pasan_por_el_filtro():
    """De extremo a extremo, sin gastar cuota.

    Se toma el texto que la recuperacion entregaria al modelo y se comprueba que
    el filtro lo limpia. No se llama al LLM: lo que se prueba es que si el modelo
    copiara un fragmento literalmente, el dato sensible no saldria igual.
    """
    ruta = RAIZ / "indice" / "fragmentos.json"
    if not ruta.exists():
        pytest.skip("no hay indice; ejecuta python -m asistente.ingesta")
    fragmentos = json.loads(ruta.read_text(encoding="utf-8"))
    sucios = [f for f in fragmentos if sanear(f["texto"])[1]]
    assert sucios, "ningun fragmento indexado tiene datos sensibles"
    for f in sucios:
        saneado, _ = sanear(f["texto"])
        assert "i-0314ddd12fadeb125" not in saneado
        assert "admin123" not in saneado

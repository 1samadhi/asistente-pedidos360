"""Comprueba que cada modo apunta a donde debe.

El error que estas pruebas evitan ya se cometio: la documentacion decia que para
trabajar en local bastaba con apuntar PEDIDOS360_URL a localhost:8082, y era
falso. Los microservicios exponen /api/v1/... —el prefijo /v1 lo inventa el API
Gateway al reenviar— y ademas viven en puertos distintos, porque el gateway era
quien los unificaba bajo un solo host.

No se llama a la API: se comprueba como se arma la URL, que es donde estuvo el
fallo.
"""
import importlib

import pytest


def recargar(monkeypatch, **entorno):
    for k in ("PEDIDOS360_MODO", "PEDIDOS360_URL", "PEDIDOS360_PEDIDOS_URL",
              "PEDIDOS360_PRODUCTOS_URL", "PEDIDOS360_AUTH_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in entorno.items():
        monkeypatch.setenv(k, v)
    from asistente import config
    return importlib.reload(config)


def test_gateway_unifica_los_servicios_bajo_v1(monkeypatch):
    c = recargar(monkeypatch, PEDIDOS360_URL="https://api.ejemplo.com/desarrollo")
    assert c.PREFIJO == "/v1"
    assert c.URL_PEDIDOS == c.URL_PRODUCTOS == "https://api.ejemplo.com/desarrollo"
    assert f"{c.URL_PEDIDOS}{c.PREFIJO}/pedidos" == \
        "https://api.ejemplo.com/desarrollo/v1/pedidos"


def test_directo_usa_api_v1_y_un_puerto_por_servicio(monkeypatch):
    c = recargar(monkeypatch, PEDIDOS360_MODO="directo")
    assert c.PREFIJO == "/api/v1"
    assert c.URL_PEDIDOS.endswith(":8082")
    assert c.URL_PRODUCTOS.endswith(":8081")
    assert c.URL_PEDIDOS != c.URL_PRODUCTOS, "el gateway ya no los unifica"
    assert f"{c.URL_PEDIDOS}{c.PREFIJO}/pedidos" == "http://localhost:8082/api/v1/pedidos"


def test_directo_se_autentica_con_el_idp_propio(monkeypatch):
    """Sin gateway no hay autorizador de Entra: basta el login de ms-auth."""
    c = recargar(monkeypatch, PEDIDOS360_MODO="directo")
    monkeypatch.setenv("MS_AUTH_PASSWORD", "loquesea")
    c = importlib.reload(c)
    assert c.hay_credenciales_api(), "en modo directo solo hace falta MS_AUTH_PASSWORD"


def test_sin_credenciales_no_se_finge_que_las_hay(monkeypatch):
    c = recargar(monkeypatch, PEDIDOS360_MODO="directo")
    monkeypatch.setenv("MS_AUTH_PASSWORD", "")
    c = importlib.reload(c)
    assert not c.hay_credenciales_api()


@pytest.fixture(autouse=True)
def _restaurar():
    yield
    from asistente import config
    importlib.reload(config)

"""Pruebas unitarias de las herramientas, con la API simulada.

El equivalente en Python de Mockito es unittest.mock, incluido en la biblioteca
estandar. La correspondencia es directa:

    Mockito                          unittest.mock
    ------------------------------   ---------------------------------------
    @Mock / mock(Clase.class)        patch(...) / MagicMock()
    when(x.metodo()).thenReturn(v)   m.return_value = v
    when(...).thenThrow(e)           m.side_effect = e
    thenReturn(a, b)  (secuencia)    m.side_effect = [a, b]
    verify(x).metodo(args)           m.assert_called_once_with(args)
    verify(x, never()).metodo()      m.assert_not_called()
    ArgumentCaptor                   m.call_args

Por que simular: estas herramientas llaman a una API desplegada en un
laboratorio de AWS que se apaga solo. Una prueba que dependa de ella falla por
motivos que no tienen nada que ver con el codigo. Con la API simulada, las
pruebas comprueban la logica —el ranking, el manejo de errores, las cabeceras—
y corren sin red, en milisegundos.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from asistente import herramientas
from asistente.herramientas import ApiNoDisponible

CATALOGO = [
    {"id": 1, "nombre": "Teclado mecanico", "precio": 45990},
    {"id": 2, "nombre": "Mouse inalambrico", "precio": 19990},
    {"id": 3, "nombre": "Monitor 27 pulgadas", "precio": 189990},
]


@pytest.fixture(autouse=True)
def _sin_token_cacheado():
    """Cada prueba empieza sin token en cache, para que no se contaminen."""
    herramientas._token_cache.clear()
    yield
    herramientas._token_cache.clear()


def api_simulada(pedidos, catalogo=CATALOGO):
    """Devuelve lo que responderia la API segun la ruta pedida.

    Equivale a encadenar varios when(...).thenReturn(...) en Mockito, uno por ruta.
    """
    def responder(ruta, base=None):
        return {"/pedidos": pedidos, "/productos": catalogo}[ruta]
    return responder


# ---------------------------------------------------------------------------
# Logica de negocio: el ranking
# ---------------------------------------------------------------------------

@patch("asistente.herramientas._get")
def test_el_que_mas_factura_no_es_el_mas_pedido(mock_get):
    """El caso del bug real que se corrigio.

    El mouse tiene mas pedidos, pero el monitor factura mas por su precio. Antes,
    con la lista ordenada por cantidad, el modelo respondia el mouse.
    """
    mock_get.side_effect = api_simulada(pedidos=[
        {"productoId": 2, "cantidad": 1},   # mouse    19.990
        {"productoId": 2, "cantidad": 1},   # mouse    19.990
        {"productoId": 2, "cantidad": 1},   # mouse    19.990  -> 3 pedidos, 59.970
        {"productoId": 3, "cantidad": 1},   # monitor 189.990  -> 1 pedido, 189.990
    ])

    resultado = herramientas.consultar_pedidos()

    assert "El que MAS FACTURA es Monitor 27 pulgadas" in resultado
    assert "El MAS PEDIDO es Mouse inalambrico" in resultado


@patch("asistente.herramientas._get")
def test_calcula_el_total_facturado(mock_get):
    mock_get.side_effect = api_simulada(pedidos=[
        {"productoId": 1, "cantidad": 2},   # 2 x 45.990 =  91.980
        {"productoId": 3, "cantidad": 1},   # 1 x 189.990 = 189.990
    ])

    resultado = herramientas.consultar_pedidos()

    assert "2 en total, $281.970 facturados" in resultado


@patch("asistente.herramientas._get")
def test_comercio_sin_pedidos(mock_get):
    mock_get.side_effect = api_simulada(pedidos=[])

    assert herramientas.consultar_pedidos() == "El comercio no tiene pedidos registrados."


# ---------------------------------------------------------------------------
# Manejo de errores: nunca inventar cifras
# ---------------------------------------------------------------------------

@patch("asistente.herramientas._get")
def test_api_caida_no_inventa_datos(mock_get):
    """Lo que paso de verdad cuando se apago el laboratorio: la API respondio 503.

    Equivale a when(api.get(...)).thenThrow(...) en Mockito.
    """
    mock_get.side_effect = ApiNoDisponible("La API respondio 503 en /pedidos.")

    resultado = herramientas.consultar_pedidos()

    assert resultado.startswith("NO DISPONIBLE")
    assert "503" in resultado
    assert "No inventes datos" in resultado
    assert "$" not in resultado, "no debe aparecer ninguna cifra"


@patch("asistente.herramientas._get")
def test_catalogo_con_api_caida(mock_get):
    mock_get.side_effect = ApiNoDisponible("No se pudo contactar la API.")

    assert herramientas.consultar_catalogo().startswith("NO DISPONIBLE")


# ---------------------------------------------------------------------------
# Interaccion con la API: verify
# ---------------------------------------------------------------------------

@patch("asistente.herramientas._token", return_value="token-falso")
@patch("asistente.herramientas.urllib.request.urlopen")
def test_envia_el_token_en_la_cabecera(mock_urlopen, mock_token):
    """Verifica COMO se llama a la API, no solo lo que devuelve.

    Es el equivalente de verify() y ArgumentCaptor en Mockito.
    """
    respuesta = MagicMock()
    respuesta.__enter__.return_value.read.return_value = json.dumps(CATALOGO).encode()
    mock_urlopen.return_value = respuesta

    herramientas._get("/productos")

    mock_urlopen.assert_called_once()
    peticion = mock_urlopen.call_args.args[0]          # ArgumentCaptor
    assert peticion.get_header("Authorization") == "Bearer token-falso"
    assert peticion.full_url.endswith("/productos")


@patch("asistente.herramientas.config")
def test_sin_credenciales_no_llama_a_la_api(mock_config):
    """Si faltan credenciales, falla antes de tocar la red.

    Equivale a verify(api, never()).get(...) en Mockito.
    """
    mock_config.hay_credenciales_api.return_value = False
    mock_config.MODO_API = "gateway"

    with patch("asistente.herramientas.urllib.request.urlopen") as mock_urlopen:
        with pytest.raises(ApiNoDisponible, match="No hay"):
            herramientas._token()
        mock_urlopen.assert_not_called()


@patch("asistente.herramientas._token_ms_auth", return_value="tok-123")
@patch("asistente.herramientas.config")
def test_el_token_se_pide_una_sola_vez(mock_config, mock_login):
    """El token se cachea: tres consultas, un solo login."""
    mock_config.hay_credenciales_api.return_value = True
    mock_config.MODO_API = "directo"

    for _ in range(3):
        assert herramientas._token() == "tok-123"

    mock_login.assert_called_once()                    # verify(times(1))

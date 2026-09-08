"""Herramientas del agente: consultas al Pedidos360 en vivo.

Estas responden lo que ningun documento puede responder, porque depende del
estado actual del sistema. Si la API no contesta, la herramienta lo dice: nunca
devuelve un numero inventado, que es exactamente la falla que la evaluacion del
sistema debe descartar.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from asistente import config

_token_cache: dict[str, str] = {}


class ApiNoDisponible(RuntimeError):
    pass


def _token() -> str:
    """Token de Entra ID.

    Las rutas de negocio del API Gateway estan enlazadas al autorizador de Entra,
    no al del IdP propio de Pedidos360: un token de ms-auth, aun siendo valido,
    recibe 401 en /v1/pedidos.
    """
    if "valor" in _token_cache:
        return _token_cache["valor"]
    if not config.hay_credenciales_api():
        raise ApiNoDisponible("No hay credenciales de Entra ID configuradas.")
    datos = urllib.parse.urlencode({
        "client_id": config.ENTRA_CLIENT_ID,
        "scope": f"{config.ENTRA_APP_ID_URI}/.default",
        "username": config.ENTRA_USUARIO,
        "password": config.ENTRA_PASSWORD,
        "grant_type": "password",
    }).encode()
    url = f"https://login.microsoftonline.com/{config.ENTRA_TENANT_ID}/oauth2/v2.0/token"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=datos), timeout=30) as r:
            _token_cache["valor"] = json.load(r)["access_token"]
    except Exception as exc:
        raise ApiNoDisponible(f"No se pudo obtener el token: {exc}") from exc
    return _token_cache["valor"]


def _get(ruta: str):
    peticion = urllib.request.Request(
        f"{config.PEDIDOS360_URL}{ruta}",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        raise ApiNoDisponible(f"La API respondio {exc.code} en {ruta}.") from exc
    except Exception as exc:
        raise ApiNoDisponible(f"No se pudo contactar la API: {exc}") from exc


def consultar_catalogo() -> str:
    try:
        productos = _get("/v1/productos")
    except ApiNoDisponible as exc:
        return f"NO DISPONIBLE: {exc} No inventes datos; dilo al usuario."
    lineas = [f"- id {p['id']}: {p['nombre']} — ${p['precio']:,}".replace(",", ".")
              for p in productos]
    return f"Catalogo actual ({len(productos)} productos):\n" + "\n".join(lineas)


def consultar_pedidos() -> str:
    try:
        pedidos = _get("/v1/pedidos")
        productos = {p["id"]: p for p in _get("/v1/productos")}
    except ApiNoDisponible as exc:
        return f"NO DISPONIBLE: {exc} No inventes datos; dilo al usuario."
    if not pedidos:
        return "El comercio no tiene pedidos registrados."

    resumen: dict[int, dict] = {}
    for p in pedidos:
        r = resumen.setdefault(p["productoId"], {"pedidos": 0, "unidades": 0})
        r["pedidos"] += 1
        r["unidades"] += p["cantidad"]

    lineas, total = [], 0
    for pid, r in sorted(resumen.items(), key=lambda kv: -kv[1]["pedidos"]):
        prod = productos.get(pid, {"nombre": f"producto {pid}", "precio": 0})
        monto = r["unidades"] * prod["precio"]
        total += monto
        lineas.append(f"- {prod['nombre']}: {r['pedidos']} pedidos, "
                      f"{r['unidades']} unidades, ${monto:,}".replace(",", "."))
    return (f"Pedidos del comercio ({len(pedidos)} en total):\n" + "\n".join(lineas)
            + f"\nMonto total: ${total:,}".replace(",", "."))

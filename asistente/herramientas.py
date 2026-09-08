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
    """Resumen de los pedidos del comercio, con los rankings ya calculados.

    El ordenamiento se hace aqui y no se delega al modelo. Medido: entregandole
    una lista ordenada por cantidad de pedidos y pidiendole "cual factura mas",
    el modelo devolvia el primero de la lista en vez del maximo por monto. Un
    LLM no es una calculadora; lo que se puede computar, se computa.
    """
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

    filas = []
    for pid, r in resumen.items():
        prod = productos.get(pid, {"nombre": f"producto {pid}", "precio": 0})
        filas.append({
            "nombre": prod["nombre"],
            "pedidos": r["pedidos"],
            "unidades": r["unidades"],
            "monto": r["unidades"] * prod["precio"],
        })

    def pesos(n):
        return f"${n:,}".replace(",", ".")

    total = sum(f["monto"] for f in filas)
    por_monto = sorted(filas, key=lambda f: -f["monto"])
    por_pedidos = sorted(filas, key=lambda f: -f["pedidos"])

    lineas = [f"Pedidos del comercio: {len(pedidos)} en total, {pesos(total)} facturados.",
              "",
              "Ranking por facturacion (de mayor a menor):"]
    for i, f in enumerate(por_monto, 1):
        lineas.append(f"  {i}. {f['nombre']}: {pesos(f['monto'])} "
                      f"({f['unidades']} unidades en {f['pedidos']} pedidos)")
    lineas += ["", "Ranking por cantidad de pedidos (de mayor a menor):"]
    for i, f in enumerate(por_pedidos, 1):
        lineas.append(f"  {i}. {f['nombre']}: {f['pedidos']} pedidos")
    lineas += ["",
               f"El que MAS FACTURA es {por_monto[0]['nombre']} con {pesos(por_monto[0]['monto'])}.",
               f"El MAS PEDIDO es {por_pedidos[0]['nombre']} con {por_pedidos[0]['pedidos']} pedidos.",
               "Usa estos rankings tal como estan; no los recalcules."]
    return "\n".join(lineas)

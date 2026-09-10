"""Comprueba el estado de la API de Pedidos360 e imprime un reporte reenviable.

    python scripts/verificar_api.py

Pensado para dos cosas: saber antes de trabajar si la API responde, y tener algo
concreto que mandarle a quien mantiene Pedidos360 cuando no responde. El reporte
distingue si el fallo esta en el borde o detras de el, que es la primera
pregunta que hara esa persona.

Salida 0 si todo responde, 1 si algo falla.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asistente import config  # noqa: E402

PUBLICAS = ["/v1/public", "/.well-known/openid-configuration", "/.well-known/jwks.json"]
PROTEGIDAS = ["/v1/productos", "/v1/pedidos"]


def probar(url: str, cabeceras: dict | None = None) -> tuple[int, float, str]:
    inicio = time.monotonic()
    peticion = urllib.request.Request(url, headers=cabeceras or {})
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            return r.status, time.monotonic() - inicio, r.read(400).decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, time.monotonic() - inicio, e.read(200).decode(errors="replace")
    except Exception as e:
        return 0, time.monotonic() - inicio, str(e)


def token_entra() -> tuple[str, str]:
    if not config.hay_credenciales_api():
        return "", "sin credenciales de Entra en el .env"
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
            return json.load(r)["access_token"], ""
    except Exception as e:
        return "", f"no se pudo obtener el token: {e}"


def diagnostico(codigo: int, ruta: str) -> str:
    """Traduce el codigo a la causa probable, para no hacerlo a mano cada vez."""
    if codigo == 200:
        return ""
    if codigo == 0:
        return "sin respuesta: revisar si el API Gateway existe y hay red"
    if codigo == 503:
        return ("el gateway responde pero la integracion no: la EC2 probablemente "
                "cambio de IP publica -> scripts/actualizar-api-gateway.sh")
    if codigo == 401:
        return ("rechazado en el borde por el autorizador. Las rutas de negocio usan "
                "el de Entra ID; un token de ms-auth da 401 aunque sea valido")
    if codigo == 404:
        return f"{ruta} no es una ruta del gateway (ojo: es /v1/..., no /api/v1/...)"
    if 500 <= codigo < 600:
        return "error del microservicio detras del gateway: revisar sus logs en la EC2"
    return "revisar"


def main() -> int:
    print("Verificacion de la API de Pedidos360")
    print(f"Base: {config.PEDIDOS360_URL}\n")

    fallos = []
    print("Rutas publicas")
    for ruta in PUBLICAS:
        codigo, t, _ = probar(f"{config.PEDIDOS360_URL}{ruta}")
        marca = "ok  " if codigo == 200 else "FALLA"
        print(f"  {marca} {ruta:38} HTTP {codigo}  {t:.2f}s")
        if codigo != 200:
            fallos.append((ruta, codigo))

    print("\nRutas protegidas")
    token, error = token_entra()
    if not token:
        print(f"  no se pudieron probar: {error}")
        fallos.append(("token de Entra", 0))
    else:
        print(f"  token de Entra obtenido ({len(token)} caracteres)")
        cab = {"Authorization": f"Bearer {token}"}
        for ruta in PROTEGIDAS:
            codigo, t, cuerpo = probar(f"{config.PEDIDOS360_URL}{ruta}", cab)
            marca = "ok  " if codigo == 200 else "FALLA"
            extra = ""
            if codigo == 200 and ruta == "/v1/pedidos":
                try:
                    extra = f"  ({len(json.loads(cuerpo))}+ pedidos)"
                except Exception:
                    extra = ""
            print(f"  {marca} {ruta:38} HTTP {codigo}  {t:.2f}s{extra}")
            if codigo != 200:
                fallos.append((ruta, codigo))

    print()
    if not fallos:
        print("Todo responde. Nada que reportar.")
        return 0

    print("=" * 66)
    print("REPORTE PARA QUIEN MANTIENE PEDIDOS360 (copiar desde aqui)")
    print("=" * 66)
    print(f"Base probada: {config.PEDIDOS360_URL}")
    for ruta, codigo in fallos:
        print(f"\n- {ruta} -> HTTP {codigo}")
        print(f"  {diagnostico(codigo, ruta)}")
    print("\nProbado con: python scripts/verificar_api.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Puebla Pedidos360 con pedidos de demostracion via su API publica.

Se autentica contra Entra ID igual que scripts/probar-endpoints.sh y crea
pedidos con una distribucion realista: los productos baratos se piden mas
seguido y en mas unidades que los caros.

La API no permite fijar la fecha (Pedido.creado = Instant.now()), asi que
todos los pedidos quedan con la marca de tiempo de la ejecucion.
"""
import json
import os
import random
import urllib.parse
import urllib.request

BASE = "https://j37oj1wn16.execute-api.us-east-1.amazonaws.com/desarrollo"

# (id, nombre, peso en la muestra, cantidad maxima por pedido)
CATALOGO = [
    (1, "Teclado mecanico", 3, 3),
    (2, "Mouse inalambrico", 5, 5),
    (3, "Monitor 27 pulgadas", 1, 2),
    (4, "Audifonos con cancelacion de ruido", 2, 3),
]


def cargar_env(ruta):
    valores = {}
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def pedir_token(env, usuario, password):
    datos = urllib.parse.urlencode({
        "client_id": env["ENTRA_CLIENT_ID"],
        "scope": f"{env['ENTRA_APP_ID_URI']}/.default",
        "username": usuario,
        "password": password,
        "grant_type": "password",
    }).encode()
    url = f"https://login.microsoftonline.com/{env['ENTRA_TENANT_ID']}/oauth2/v2.0/token"
    with urllib.request.urlopen(urllib.request.Request(url, data=datos), timeout=30) as r:
        return json.load(r)["access_token"]


def crear_pedido(token, producto_id, cantidad):
    cuerpo = json.dumps({"productoId": producto_id, "cantidad": cantidad}).encode()
    peticion = urllib.request.Request(
        f"{BASE}/v1/pedidos",
        data=cuerpo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def main():
    env = cargar_env(os.environ["RUTA_ENV"])
    random.seed(360)  # reproducible: la misma muestra en cada ejecucion

    comercios = [
        ("comercio cliente", env["ENTRA_USUARIO_CLIENTE"], env["ENTRA_PASSWORD_CLIENTE"], 55),
        ("comercio admin", env["ENTRA_USUARIO_ADMIN"], env["ENTRA_PASSWORD_ADMIN"], 30),
    ]

    ids = [p[0] for p in CATALOGO]
    pesos = [p[2] for p in CATALOGO]
    topes = {p[0]: p[3] for p in CATALOGO}

    total_ok = 0
    for etiqueta, usuario, password, cuantos in comercios:
        try:
            token = pedir_token(env, usuario, password)
        except Exception as exc:
            print(f"  {etiqueta}: no se pudo obtener token ({exc})")
            continue
        ok = fallos = 0
        for _ in range(cuantos):
            pid = random.choices(ids, weights=pesos)[0]
            cantidad = random.randint(1, topes[pid])
            codigo, _cuerpo = crear_pedido(token, pid, cantidad)
            if codigo == 201:
                ok += 1
            else:
                fallos += 1
                if fallos <= 2:
                    print(f"  {etiqueta}: fallo {codigo} -> {_cuerpo}")
        print(f"  {etiqueta}: {ok} creados, {fallos} fallidos")
        total_ok += ok
    print(f"\nTotal creado: {total_ok}")


if __name__ == "__main__":
    main()

"""Calibracion del juez: comprueba que la rubrica discrimina de verdad.

    python -m evaluacion.calibrar_juez

Un juez que solo sabe decir 0 o 1 no sirve para comparar dos versiones buenas
del sistema. Se le dan cuatro respuestas construidas a proposito —correcta,
correcta pero incompleta, con un dato inventado, y falsa— y se exige que las
ordene de mayor a menor. Si no las ordena, la rubrica no discrimina y hay que
reescribirla antes de usarla para decidir nada.
"""
from langchain_groq import ChatGroq

from asistente import config
from evaluacion.evaluar import JUEZ_FIDELIDAD, JUEZ_RELEVANCIA, _nota

CONTEXTO = """[1] 09-errores-frecuentes.md · documentacion propia
### Token del IdP propio (ms-auth)
Un POST con usuario y contrasena en JSON, y nada mas. No lleva client_id, scope
ni grant_type: /auth/login no es un endpoint de OAuth estandar, es el login del
IdP. Devuelve access_token firmado en RS256, con audiencia exp1-api."""

PREGUNTA = "Como obtengo un token del IdP propio de Pedidos360?"
REFERENCIA = ("Con POST /auth/login enviando usuario y contrasena en JSON, sin "
              "client_id ni grant_type.")

CASOS = [
    ("correcta",
     "Haz POST a /auth/login con usuario y contrasena en JSON. No lleva client_id "
     "ni grant_type. Devuelve un access_token firmado en RS256."),
    ("incompleta",
     "Tienes que autenticarte contra el IdP propio para conseguir un token."),
    ("con dato inventado",
     "Haz POST a /auth/login con usuario y contrasena en JSON. El token caduca a "
     "los 15 minutos y se renueva en /auth/refresh con el refresh_token."),
    ("falsa",
     "Pide el token a https://login.microsoftonline.com/oauth2/v2.0/token con "
     "client_id, scope y grant_type=password."),
]


def main():
    juez = ChatGroq(model=config.MODELO_RAPIDO, temperature=0, reasoning_effort="low")
    print(f"Calibracion del juez ({config.MODELO_RAPIDO})\n")
    print(f"  {'caso':22} {'fidelidad':>10} {'relevancia':>11}")
    fid, rel = [], []
    for etiqueta, respuesta in CASOS:
        f = _nota(juez.invoke(JUEZ_FIDELIDAD.format(
            contexto=CONTEXTO, respuesta=respuesta)).content)
        r = _nota(juez.invoke(JUEZ_RELEVANCIA.format(
            pregunta=PREGUNTA, respuesta=respuesta, referencia=REFERENCIA)).content)
        fid.append(f); rel.append(r)
        print(f"  {etiqueta:22} {f!s:>10} {r!s:>11}")

    print()
    ok = True
    if len(set(fid)) < 3:
        print(f"  FALLA fidelidad: solo {len(set(fid))} valores distintos, no gradua")
        ok = False
    if fid[0] is None or fid[3] is None or not (fid[0] > fid[3]):
        print("  FALLA fidelidad: no separa la correcta de la falsa")
        ok = False
    if rel[0] is None or rel[1] is None or not (rel[0] > rel[1]):
        print("  FALLA relevancia: no penaliza la incompleta")
        ok = False
    if ok:
        print("  La rubrica discrimina: sirve para comparar variantes.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

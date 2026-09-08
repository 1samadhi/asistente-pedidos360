"""Evaluacion del asistente sobre el set de 30 preguntas.

    python -m evaluacion.evaluar                 # solo recuperacion (sin LLM)
    python -m evaluacion.evaluar --generacion    # agrega fidelidad y relevancia
    python -m evaluacion.evaluar --generacion --n 5

Se separa en dos bloques a proposito:

- **Recuperacion.** No usa el modelo: compara los archivos recuperados contra los
  que el set declara como correctos. Es gratis y determinista, asi que corre
  sobre las 30 preguntas y permite comparar configuraciones cuantas veces haga
  falta. Mide las dos estrategias, solo-semantica e hibrida, sobre las mismas
  preguntas.

- **Generacion.** Fidelidad y relevancia se evaluan con un modelo como juez, y
  eso consume cuota. La capa gratuita de Groq son 200.000 tokens diarios, asi
  que por defecto corre sobre una submuestra y con el modelo rapido. Ampliar la
  muestra es subir --n, no cambiar codigo.

Metricas de recuperacion, por pregunta:
  context recall     de los archivos que debian aparecer, cuantos aparecieron
  context precision  de los fragmentos recuperados, cuantos vienen de un archivo correcto
"""
import argparse
import json
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SET = Path(__file__).resolve().parent / "preguntas.jsonl"


def cargar_set() -> list[dict]:
    with open(SET, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# --------------------------------------------------------------------------
# Recuperacion
# --------------------------------------------------------------------------

def _archivos(documentos) -> list[str]:
    salida = []
    for d in documentos:
        if isinstance(d, tuple):
            d = d[0]
        salida.append(d.metadata["archivo"])
    return salida


def evaluar_recuperacion(casos: list[dict]) -> dict:
    from asistente.recuperador import cargar_indice, recuperar, recuperar_hibrido

    almacen = cargar_indice()
    estrategias = {
        "solo semantica": lambda p: recuperar(p, k=5, almacen=almacen),
        "hibrida ponderada": lambda p: recuperar_hibrido(p, almacen=almacen),
    }

    resultados = {}
    for nombre, fn in estrategias.items():
        recalls, precisiones, fallos = [], [], []
        for caso in casos:
            recuperados = _archivos(fn(caso["pregunta"]))
            esperados = set(caso["fuentes"])
            aciertos = esperados & set(recuperados)
            recall = len(aciertos) / len(esperados)
            precision = sum(1 for a in recuperados if a in esperados) / len(recuperados)
            recalls.append(recall)
            precisiones.append(precision)
            if recall == 0:
                fallos.append(caso)
        resultados[nombre] = {
            "recall": statistics.mean(recalls),
            "precision": statistics.mean(precisiones),
            "sin_ninguna_fuente": fallos,
        }
    return resultados


# --------------------------------------------------------------------------
# Generacion (modelo como juez)
# --------------------------------------------------------------------------

JUEZ_FIDELIDAD = """Eres un evaluador estricto. Recibes un CONTEXTO y una RESPUESTA.
Responde solo con un numero entre 0 y 1: que proporcion de las afirmaciones de la
RESPUESTA se puede verificar en el CONTEXTO. Si la respuesta afirma cosas que el
contexto no dice, baja la nota. No expliques nada, devuelve solo el numero.

CONTEXTO:
{contexto}

RESPUESTA:
{respuesta}"""

JUEZ_RELEVANCIA = """Eres un evaluador estricto. Recibes una PREGUNTA, una RESPUESTA
y la RESPUESTA DE REFERENCIA. Responde solo con un numero entre 0 y 1: cuanto
responde la RESPUESTA a la PREGUNTA, comparada con la referencia. Una respuesta
correcta pero incompleta merece nota media. No expliques nada, devuelve solo el numero.

PREGUNTA: {pregunta}

RESPUESTA: {respuesta}

RESPUESTA DE REFERENCIA: {referencia}"""


def _nota(texto: str) -> float | None:
    import re
    m = re.search(r"(\d(?:[.,]\d+)?)", texto)
    if not m:
        return None
    try:
        return max(0.0, min(1.0, float(m.group(1).replace(",", "."))))
    except ValueError:
        return None


def evaluar_generacion(casos: list[dict], n: int) -> dict:
    from langchain_groq import ChatGroq

    from asistente import config
    from asistente.agente import crear_agente, preguntar
    from asistente.recuperador import (
        cargar_indice, formatear_contexto, recuperar_hibrido,
    )

    # Submuestra estable: se toma una de cada k para cubrir todos los tipos.
    paso = max(1, len(casos) // n)
    muestra = casos[::paso][:n]

    almacen = cargar_indice()
    ejecutor = crear_agente()
    juez = ChatGroq(model=config.MODELO_RAPIDO, temperature=0, reasoning_effort="low")

    fidelidades, relevancias, detalle = [], [], []
    for caso in muestra:
        respuesta = preguntar(caso["pregunta"], ejecutor)
        contexto = formatear_contexto(recuperar_hibrido(caso["pregunta"], almacen=almacen))

        f = _nota(juez.invoke(JUEZ_FIDELIDAD.format(
            contexto=contexto[:6000], respuesta=respuesta)).content)
        r = _nota(juez.invoke(JUEZ_RELEVANCIA.format(
            pregunta=caso["pregunta"], respuesta=respuesta,
            referencia=caso["referencia"])).content)

        if f is not None:
            fidelidades.append(f)
        if r is not None:
            relevancias.append(r)
        detalle.append({"id": caso["id"], "fidelidad": f, "relevancia": r,
                        "pregunta": caso["pregunta"], "respuesta": respuesta})

    return {
        "n": len(muestra),
        "fidelidad": statistics.mean(fidelidades) if fidelidades else None,
        "relevancia": statistics.mean(relevancias) if relevancias else None,
        "detalle": detalle,
    }


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generacion", action="store_true",
                    help="evalua tambien fidelidad y relevancia (consume cuota)")
    ap.add_argument("--n", type=int, default=10,
                    help="tamano de la submuestra para generacion")
    ap.add_argument("--guardar", type=str, default="",
                    help="ruta de un JSON donde volcar el detalle")
    args = ap.parse_args()

    casos = cargar_set()
    print(f"Set de evaluacion: {len(casos)} preguntas "
          f"({sum(1 for c in casos if c['tipo'] == 'documental')} sobre documentacion propia, "
          f"{sum(1 for c in casos if c['tipo'] == 'externa')} sobre fuentes externas)\n")

    print("RECUPERACION")
    print(f"  {'estrategia':18} {'recall':>8} {'precision':>10} {'sin fuente':>11}")
    recuperacion = evaluar_recuperacion(casos)
    for nombre, r in recuperacion.items():
        print(f"  {nombre:18} {r['recall']:>8.2f} {r['precision']:>10.2f} "
              f"{len(r['sin_ninguna_fuente']):>11}")

    fallos = recuperacion["hibrida ponderada"]["sin_ninguna_fuente"]
    if fallos:
        print("\n  Preguntas donde no entro ninguna fuente esperada:")
        for c in fallos:
            print(f"    [{c['id']:>2}] {c['pregunta'][:66]}")

    salida = {"recuperacion": {k: {kk: vv for kk, vv in v.items()
                                   if kk != "sin_ninguna_fuente"}
                               for k, v in recuperacion.items()}}

    if args.generacion:
        print(f"\nGENERACION (submuestra de {args.n}, juez: modelo rapido)")
        g = evaluar_generacion(casos, args.n)
        print(f"  fidelidad (faithfulness):  {g['fidelidad']:.2f}"
              if g["fidelidad"] is not None else "  fidelidad: sin datos")
        print(f"  relevancia (answer relevancy): {g['relevancia']:.2f}"
              if g["relevancia"] is not None else "  relevancia: sin datos")
        salida["generacion"] = g

    if args.guardar:
        Path(args.guardar).write_text(
            json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nDetalle guardado en {args.guardar}")


if __name__ == "__main__":
    main()

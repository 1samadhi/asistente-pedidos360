"""Compara las variantes del prompt de sistema sobre el mismo set.

    python -m evaluacion.comparar_prompts --n 8

Las tres variantes se miden con el mismo juez graduado, la misma submuestra y la
misma recuperacion: lo unico que cambia es el prompt. Los resultados se guardan
en evaluacion/resultados-prompts.json a medida que se obtienen, para no perder
el trabajo si se agota la cuota a mitad de camino.
"""
import argparse
import json
import statistics
from pathlib import Path

from langchain_groq import ChatGroq

from asistente import config
from asistente.agente import crear_agente, preguntar
from asistente.prompts import VARIANTES
from asistente.recuperador import cargar_indice, formatear_contexto, recuperar_hibrido
from evaluacion.evaluar import JUEZ_FIDELIDAD, JUEZ_RELEVANCIA, _nota, cargar_set

SALIDA = Path(__file__).resolve().parent / "resultados-prompts.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()

    casos = cargar_set()
    paso = max(1, len(casos) // args.n)
    muestra = casos[::paso][:args.n]

    almacen = cargar_indice()
    juez = ChatGroq(model=config.MODELO_RAPIDO, temperature=0, reasoning_effort="low")

    # El contexto no depende del prompt: se calcula una vez y se reutiliza.
    contextos = {c["id"]: formatear_contexto(recuperar_hibrido(c["pregunta"], almacen=almacen))
                 for c in muestra}

    todo = {}
    print(f"Comparando {len(VARIANTES)} variantes sobre {len(muestra)} preguntas\n")
    for nombre, sistema in VARIANTES.items():
        ejecutor = crear_agente(sistema=sistema)
        fid, rel, detalle = [], [], []
        for caso in muestra:
            try:
                respuesta = preguntar(caso["pregunta"], ejecutor)
            except Exception as exc:
                print(f"  [{caso['id']}] error: {exc}")
                continue
            f = _nota(juez.invoke(JUEZ_FIDELIDAD.format(
                contexto=contextos[caso["id"]][:6000], respuesta=respuesta)).content)
            r = _nota(juez.invoke(JUEZ_RELEVANCIA.format(
                pregunta=caso["pregunta"], respuesta=respuesta,
                referencia=caso["referencia"])).content)
            if f is not None:
                fid.append(f)
            if r is not None:
                rel.append(r)
            detalle.append({"id": caso["id"], "fidelidad": f, "relevancia": r,
                            "respuesta": respuesta})
        todo[nombre] = {
            "fidelidad": statistics.mean(fid) if fid else None,
            "relevancia": statistics.mean(rel) if rel else None,
            "n": len(detalle),
            "detalle": detalle,
        }
        m = todo[nombre]
        print(f"  {nombre:22} fidelidad {m['fidelidad']:.2f}  relevancia {m['relevancia']:.2f}")
        SALIDA.write_text(json.dumps(todo, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'variante':22} {'fidelidad':>10} {'relevancia':>11} {'media':>8}")
    for nombre, m in sorted(todo.items(),
                            key=lambda kv: -((kv[1]["fidelidad"] or 0) + (kv[1]["relevancia"] or 0))):
        media = ((m["fidelidad"] or 0) + (m["relevancia"] or 0)) / 2
        print(f"{nombre:22} {m['fidelidad']:>10.2f} {m['relevancia']:>11.2f} {media:>8.2f}")
    print(f"\nDetalle en {SALIDA}")


if __name__ == "__main__":
    main()

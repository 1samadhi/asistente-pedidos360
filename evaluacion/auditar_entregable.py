"""Audita el entregable contra la pauta de la EP1.

    python -m evaluacion.auditar_entregable

Comprueba lo que se puede comprobar sin criterio humano: que cada elemento que
la pauta exige exista, que las cifras citadas en los documentos coincidan con
las que produce el codigo, y que no haya quedado nada sin completar. Lo que
exige juicio —si una justificacion es buena— no se audita aqui.

Salida 0 si no falta nada obligatorio.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERDE, ROJO, AMBAR, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[0m"

fallos, avisos = [], []


def marcar(ok: bool, texto: str, obligatorio: bool = True, detalle: str = ""):
    if ok:
        print(f"  {VERDE}ok  {FIN} {texto}")
    elif obligatorio:
        fallos.append(texto)
        print(f"  {ROJO}FALTA{FIN} {texto}" + (f"  — {detalle}" if detalle else ""))
    else:
        avisos.append(texto)
        print(f"  {AMBAR}pend{FIN} {texto}" + (f"  — {detalle}" if detalle else ""))


def leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def main() -> int:
    print("Auditoria del entregable — EP1 ISY0101\n")

    # --- 1. Propuesta de caso: los siete elementos minimos ---
    print("Propuesta de caso · elementos minimos que exige la pauta")
    prop = leer(RAIZ / "propuesta-de-caso.md")
    for n, clave in [
        (1, "Nombre y breve descripción de la organización"),
        (2, "Identificación y descripción del problema"),
        (3, "Objetivos de la intervención"),
        (4, "Datos disponibles"),
        (5, "Restricciones"),
        (6, "Motivación para"),
        (7, "Referencias"),
    ]:
        marcar(clave.lower() in prop.lower(), f"{n}. {clave}")

    # --- 2. Informe: los apartados A-G ---
    print("\nInforme · apartados que exige la pauta")
    inf = leer(RAIZ / "informe" / "informe-ep1.md")
    for letra, titulo in [
        ("A", "Análisis del caso organizacional"),
        ("B", "Formulación de prompts"),
        ("C", "pipeline RAG"),
        ("D", "Arquitectura de la solución"),
        ("E", "justificación de decisiones"),
        ("F", "Conclusiones"),
        ("G", "Referencias"),
    ]:
        marcar(titulo.lower() in inf.lower(), f"{letra}. {titulo}")

    # --- 3. Aspectos formales del repositorio ---
    print("\nRepositorio · lo que la pauta pide que contenga")
    marcar((RAIZ / "README.md").exists(), "README con instrucciones de ejecución")
    marcar(len(list((RAIZ / "asistente").glob("*.py"))) >= 5, "código fuente")
    marcar((RAIZ / "docs" / "arquitectura.svg").exists(), "diagrama de arquitectura")
    bocetos = list((RAIZ / "docs").glob("boceto*")) + list((RAIZ / "docs").glob("*secuencia*"))
    marcar(bool(bocetos), "bocetos de diseño", detalle="la pauta los exige explícitamente")
    marcar((RAIZ / "evaluacion" / "test_guardrails.py").exists(), "pruebas de software")
    ev = RAIZ / "evaluacion" / "evidencias"
    marcar(ev.exists() and len(list(ev.glob("*"))) >= 2, "evidencia de las pruebas ejecutadas",
           detalle="hace falta la salida de una ejecución, no solo el código")
    marcar((RAIZ / "informe" / "informe-ep1.md").exists(), "informe")
    entregable = list((RAIZ / "informe").glob("*.pdf")) + list((RAIZ / "informe").glob("*.docx"))
    marcar(bool(entregable), "informe en Word o PDF", obligatorio=False,
           detalle="la pauta exige uno de los dos formatos")

    # --- 4. Coherencia de las cifras entre documentos y codigo ---
    print("\nCoherencia · las cifras citadas contra las reales")
    palabras_int = sum(len(p.read_text(encoding="utf-8").split())
                       for p in (RAIZ / "corpus" / "interno").glob("*.md"))
    n_int = len(list((RAIZ / "corpus" / "interno").glob("*.md")))
    readme = leer(RAIZ / "README.md")
    marcar(f"{palabras_int:,}".replace(",", ".") in readme,
           f"README cita las {palabras_int} palabras reales del corpus interno")
    marcar(f"{n_int} archivos" in readme, f"README cita los {n_int} archivos reales")

    res = RAIZ / "evaluacion" / "resultados.json"
    if res.exists():
        d = json.loads(res.read_text(encoding="utf-8"))
        rec = d["recuperacion"]["hibrida ponderada"]["recall"]
        gen = d.get("generacion", {})
        marcar(f"{rec:.2f}".replace(".", ",") in inf,
               f"informe cita el recall real ({rec:.2f})")
        if gen.get("fidelidad") is not None:
            marcar(f"{gen['fidelidad']:.2f}".replace(".", ",") in inf,
                   f"informe cita la fidelidad real ({gen['fidelidad']:.2f})")
            marcar(gen["n"] == 30, f"la generación se midió sobre las 30 preguntas (n={gen['n']})")
    else:
        marcar(False, "resultados.json presente", detalle="ejecuta evaluacion.evaluar")

    # --- 5. Marcadores sin completar ---
    print("\nSin completar · marcadores que quedan en los documentos")
    for nombre, texto in [("propuesta", prop), ("informe", inf)]:
        pendientes = re.findall(r"\[(?:completar|nombre del|Pendiente|Añadir|Ajustar)[^\]]*\]",
                                texto, re.I)
        marcar(not pendientes, f"{nombre} sin marcadores pendientes", obligatorio=False,
               detalle=f"{len(pendientes)} marcador(es): {pendientes[:2]}" if pendientes else "")

    # --- 6. Seguridad ---
    print("\nSeguridad")
    try:
        rastreados = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True,
                                    text=True, check=True).stdout.split("\n")
    except Exception:
        rastreados = []
    marcar(".env" not in [r.strip() for r in rastreados], ".env fuera del control de versiones")
    marcar(not any(r.startswith("indice/") for r in rastreados), "índice no versionado")

    # --- 7. Pruebas en verde ---
    print("\nPruebas")
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "evaluacion/", "-q"],
                           cwd=RAIZ, capture_output=True, text=True, timeout=300)
        ultima = [l for l in r.stdout.strip().split("\n") if l.strip()][-1]
        marcar(r.returncode == 0, f"pytest en verde — {ultima.strip()}")
    except Exception as exc:
        marcar(False, "pytest ejecutable", detalle=str(exc))

    print()
    if fallos:
        print(f"{ROJO}{len(fallos)} elemento(s) obligatorio(s) sin cumplir.{FIN}")
    if avisos:
        print(f"{AMBAR}{len(avisos)} pendiente(s) no bloqueante(s).{FIN}")
    if not fallos and not avisos:
        print(f"{VERDE}Todo cuadrado con la pauta.{FIN}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())

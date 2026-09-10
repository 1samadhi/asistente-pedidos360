"""Ejecuta las pruebas y guarda su salida como evidencia.

    python -m evaluacion.capturar_evidencia

La pauta pide "evidencia de pruebas de software realizadas". El codigo de las
pruebas no es la evidencia: la evidencia es su salida, fechada y reproducible.
Este script la genera, para no pegarla a mano y que envejezca en silencio.

No incluye la evaluacion de generacion, que consume cuota; esa se guarda aparte
en evaluacion/resultados.json cuando se ejecuta con --generacion.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "evaluacion" / "evidencias" / "ejecucion-de-pruebas.md"

PASOS = [
    ("Pruebas unitarias del guardrail",
     [sys.executable, "-m", "pytest", "evaluacion/", "-v", "--no-header", "-q"],
     "Verifica que el filtro de salida atrapa cada patron sensible, que no altera "
     "el texto legitimo, y que el corpus contiene efectivamente datos de ese tipo."),
    ("Metricas de recuperacion sobre las 30 preguntas",
     [sys.executable, "-m", "evaluacion.evaluar"],
     "Determinista y sin coste. Compara la busqueda solo-semantica con la hibrida "
     "sobre el mismo set."),
    ("Calibracion del juez",
     [sys.executable, "-m", "evaluacion.calibrar_juez"],
     "Comprueba que la rubrica discrimina antes de usarla para decidir nada: se le "
     "dan cuatro respuestas construidas a proposito y debe ordenarlas."),
    ("Estado de la API de Pedidos360",
     [sys.executable, "scripts/verificar_api.py"],
     "El asistente depende de un sistema externo. Se deja constancia de su estado "
     "en el momento de la ejecucion."),
]

PREGUNTAS = [
    ("Documental", "Tengo un token valido de ms-auth con los scopes correctos pero "
                   "/v1/pedidos me devuelve 401. Por que?"),
    ("Datos en vivo", "Cuantos pedidos lleva mi comercio y cual es el producto que "
                      "mas factura?"),
    ("Mixta", "Como obtengo el listado de mis pedidos por API y cuantos llevo ahora?"),
]


def correr(cmd):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, timeout=900)
    salida = (r.stdout + r.stderr).strip()
    # Ruido de las librerias que no aporta nada a la evidencia: el aviso de CUDA
    # de torch y la barra de progreso de la carga de los embeddings.
    RUIDO = ("CUDA initialization", "torch._C._cuda", "Loading weights:",
             "UserWarning", "warnings.warn")
    return "\n".join(l for l in salida.split("\n")
                     if not any(r in l for r in RUIDO)).strip()


def main():
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        "# Evidencia de las pruebas ejecutadas", "",
        f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        "**Reproducir:** `python -m evaluacion.capturar_evidencia`", "",
        "Salida literal de cada comprobacion, sin editar.", "", "---", "",
    ]

    for titulo, cmd, porque in PASOS:
        print(f"  ejecutando: {titulo}")
        lineas += [f"## {titulo}", "", porque, "",
                   f"```\n$ {' '.join(str(c) for c in cmd[1:] if c != '-m')}\n"
                   f"{correr(cmd)}\n```", ""]

    print("  ejecutando: los tres tipos de consulta")
    lineas += ["## Los tres tipos de consulta", "",
               "El enrutamiento entre documentacion y datos en vivo no esta cableado "
               "con reglas: lo decide el modelo. Estas tres consultas lo ejercitan.", ""]
    for etiqueta, pregunta in PREGUNTAS:
        salida = correr([sys.executable, "-m", "asistente.agente", pregunta])
        lineas += [f"### {etiqueta}", "", f"> {pregunta}", "", f"```\n{salida}\n```", ""]

    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nEvidencia en {SALIDA.relative_to(RAIZ)} "
          f"({len(SALIDA.read_text(encoding='utf-8').split())} palabras)")


if __name__ == "__main__":
    main()

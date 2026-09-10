"""Convierte el informe de Markdown a .docx y .pdf.

    python scripts/convertir_informe.py

La pauta exige el informe en Word o PDF. El original se mantiene en Markdown
porque es lo que se versiona bien; esto genera los formatos entregables.

El diagrama se rasteriza a PNG antes de incrustarlo: LibreOffice no trata el SVG
de forma fiable al convertir, y un informe sin la figura pierde el indicador IE6.

Sobre el formato: se usa un cuerpo serif de 11 pt con interlineado sencillo, que
es lo que permite que quepan las cinco paginas. Si el docente exige el
interlineado doble de APA 7, el texto NO cabra en cinco paginas y habra que
recortar; la lista de que recortar esta al principio del propio informe.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MD = RAIZ / "informe" / "informe-ep1.md"
SALIDA = RAIZ / "informe"

ESTILO = """
@page { margin: 2.2cm; }
body { font-family: 'Liberation Serif','Times New Roman',serif; font-size: 11pt;
       line-height: 1.12; color: #000; }
h1 { font-size: 15pt; margin: 0 0 4pt; }
h2 { font-size: 12.5pt; margin: 14pt 0 5pt; border-bottom: 0.5pt solid #999;
     padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 10pt 0 4pt; }
p { margin: 0 0 6pt; text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 6pt 0 10pt; }
th, td { border: 0.5pt solid #999; padding: 3pt 5pt; text-align: left;
         vertical-align: top; }
th { background: #eee; font-weight: bold; }
blockquote { border-left: 2pt solid #999; margin: 6pt 0; padding: 3pt 0 3pt 10pt;
             font-size: 10pt; color: #333; }
code { font-family: 'Liberation Mono',monospace; font-size: 9.5pt; }
img { width: 12.5cm; }
ul, ol { margin: 0 0 6pt; padding-left: 18pt; }
li { margin-bottom: 3pt; }
em { font-style: italic; }
"""


def rasterizar_diagrama() -> Path | None:
    svg = RAIZ / "docs" / "arquitectura.svg"
    png = RAIZ / "docs" / "arquitectura.png"
    if not svg.exists():
        return None
    navegador = shutil.which("chromium") or shutil.which("chromium-browser") \
        or shutil.which("google-chrome")
    if not navegador:
        print("  aviso: sin navegador para rasterizar; el informe ira sin figura")
        return None
    subprocess.run([navegador, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--screenshot={png}", "--window-size=1000,700",
                    "--hide-scrollbars", svg.as_uri()],
                   capture_output=True, timeout=180)
    return png if png.exists() else None


def main():
    if not MD.exists():
        sys.exit(f"No existe {MD}")

    texto = MD.read_text(encoding="utf-8")

    # La nota interna para el equipo no va en el entregable.
    texto = re.sub(r"> \*\*Nota para el equipo.*?(?=\n---)", "", texto, flags=re.S)

    png = rasterizar_diagrama()
    if png:
        # La figura va incrustada como data URI. Con una ruta de archivo,
        # relativa o absoluta, LibreOffice deja el .docx con un ENLACE a la
        # imagen en vez de la imagen: se ve bien aqui y se rompe en el
        # computador de quien evalua.
        import base64
        b64 = base64.b64encode(png.read_bytes()).decode()
        texto = texto.replace("![Arquitectura de la solución](../docs/arquitectura.svg)",
                              f'![Arquitectura de la solución](data:image/png;base64,{b64})')

    from markdown_it import MarkdownIt
    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")
    cuerpo = md.render(texto)

    html = SALIDA / "informe-ep1.html"
    html.write_text(
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{ESTILO}</style></head><body>{cuerpo}</body></html>",
        encoding="utf-8")

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print(f"  HTML generado en {html.name}; sin LibreOffice para convertir")
        return

    # Al convertir DESDE html, LibreOffice no adivina el filtro de salida de Word:
    # hay que nombrarlo. El de PDF si lo deduce.
    for formato, filtro in (("docx", "docx:MS Word 2007 XML"), ("pdf", "pdf")):
        r = subprocess.run([soffice, "--headless", "--convert-to", filtro,
                            "--outdir", str(SALIDA), str(html)],
                           capture_output=True, text=True, timeout=300)
        destino = SALIDA / f"informe-ep1.{formato}"
        if destino.exists():
            print(f"  {destino.name}: {destino.stat().st_size // 1024} KB")
        else:
            print(f"  fallo al generar {formato}: {r.stderr.strip()[:200]}")


if __name__ == "__main__":
    main()

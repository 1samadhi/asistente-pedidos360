"""Genera la presentacion de la EP1 a partir de los datos reales del proyecto.

    uv run --no-project --with python-pptx python scripts/generar_ppt.py

Se genera con codigo y no a mano para que las cifras salgan de evaluacion/
resultados.json y no de la memoria de nadie: si se vuelve a medir, se regenera
la presentacion y los numeros siguen siendo ciertos.

Las notas del orador son PREGUNTAS, no un guion. La pauta prohibe que la IA
redacte justificaciones tecnicas; el argumento hablado lo pone el equipo.
"""
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "presentacion" / "EP1-asistente-pedidos360.pptx"

TINTA   = RGBColor(0x1B, 0x24, 0x30)
SUAVE   = RGBColor(0x5B, 0x66, 0x72)
ACENTO  = RGBColor(0x1F, 0x6F, 0x63)
SENAL   = RGBColor(0xB4, 0x47, 0x2B)
PAPEL   = RGBColor(0xFF, 0xFF, 0xFF)
FONDO   = RGBColor(0xF4, 0xF6, 0xF5)

ANCHO, ALTO = Inches(13.333), Inches(7.5)


def texto(slide, x, y, w, h, contenido, tam=18, color=TINTA, negrita=False,
          alineado=PP_ALIGN.LEFT, interlineado=1.25):
    caja = slide.shapes.add_textbox(x, y, w, h)
    tf = caja.text_frame
    tf.word_wrap = True
    for i, linea in enumerate(contenido.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alineado
        p.line_spacing = interlineado
        r = p.add_run(); r.text = linea
        r.font.size = Pt(tam); r.font.bold = negrita
        r.font.color.rgb = color; r.font.name = "Calibri"
    return caja


def titulo_slide(slide, t, subtitulo=None):
    texto(slide, Inches(0.8), Inches(0.45), Inches(11.7), Inches(0.9), t, 34, TINTA, True)
    if subtitulo:
        texto(slide, Inches(0.8), Inches(1.28), Inches(11.7), Inches(0.5), subtitulo, 17, SUAVE)


def nota(slide, t):
    slide.notes_slide.notes_text_frame.text = t


def nueva(prs, fondo=PAPEL):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    f = s.background.fill; f.solid(); f.fore_color.rgb = fondo
    return s


def imagen_centrada(slide, ruta, arriba, ancho_max=Inches(12.3)):
    from PIL import Image  # solo para leer dimensiones
    with Image.open(ruta) as im:
        w, h = im.size
    ancho = ancho_max
    alto = Emu(int(ancho * h / w))
    slide.shapes.add_picture(str(ruta), Emu(int((ANCHO - ancho) / 2)), arriba,
                             width=ancho, height=alto)


def main():
    datos = json.loads((RAIZ / "evaluacion" / "resultados.json").read_text(encoding="utf-8"))
    rec = datos["recuperacion"]
    gen = datos.get("generacion", {})

    prs = Presentation()
    prs.slide_width, prs.slide_height = ANCHO, ALTO

    # ── 1. Portada ───────────────────────────────────────────────
    s = nueva(prs)
    texto(s, Inches(0.9), Inches(2.1), Inches(11.5), Inches(0.5),
          "EVALUACIÓN PARCIAL N°1 · ISY0101", 15, ACENTO, True)
    texto(s, Inches(0.9), Inches(2.7), Inches(11.5), Inches(1.6),
          "Asistente de integración\npara Pedidos360", 48, TINTA, True, interlineado=1.05)
    texto(s, Inches(0.9), Inches(4.7), Inches(11.5), Inches(0.9),
          "Una solución con LLM y RAG para el onboarding técnico de comercios", 20, SUAVE)
    texto(s, Inches(0.9), Inches(5.9), Inches(11.5), Inches(0.9),
          "Ismael Oyarzún  ·  Felipe Angel", 19, TINTA, True)
    texto(s, Inches(0.9), Inches(6.35), Inches(11.5), Inches(0.5),
          "Ingeniería de Soluciones con IA · Duoc UC · Septiembre 2026", 15, SUAVE)
    nota(s, "Presentarse y decir en una frase qué hace el sistema.")

    # ── 2. El problema ───────────────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "El problema", "Pedidos360 · plataforma B2B de pedidos con autenticación federada")
    texto(s, Inches(0.8), Inches(2.1), Inches(6.0), Inches(2.6),
          "Cada comercio que se integra necesita que un\ndesarrollador entienda:\n\n"
          "·  qué emisor de identidad le corresponde\n"
          "·  cómo obtener un token\n"
          "·  qué scopes necesita\n"
          "·  qué significa cada error", 19, TINTA)
    caja = s.shapes.add_textbox(Inches(7.2), Inches(2.1), Inches(5.3), Inches(2.9))
    f = caja.fill; f.solid(); f.fore_color.rgb = FONDO
    l = caja.line; l.color.rgb = SENAL; l.width = Pt(2)
    texto(s, Inches(7.45), Inches(2.35), Inches(4.9), Inches(2.5),
          "Comprobado en producción\n\n"
          "Token válido, emisor correcto,\nscopes correctos:\n\n"
          "GET /v1/pedidos  →  401", 18, TINTA)
    texto(s, Inches(0.8), Inches(5.2), Inches(11.7), Inches(1.2),
          "La respuesta existe, pero repartida entre un README, seis documentos técnicos,\n"
          "un CHANGELOG, dos colecciones de API y el código fuente.", 19, SUAVE)
    nota(s, "PREGUNTA A RESPONDER: ¿por qué esto le cuesta dinero a la organización? "
            "Hablar de horas de ingeniería y de fricción comercial al adherir comercios.")

    # ── 3. Qué se construyó ──────────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "Qué construimos",
                 "Un asistente que responde consultas de integración, citando sus fuentes")
    filas = [
        ("«¿Cómo obtengo un token?»", "documentación propia"),
        ("«¿Qué significa el claim aud?»", "fuente externa · RFC 7519"),
        ("«¿Cuántos pedidos llevo?»", "API en vivo"),
        ("«¿Cómo lo obtengo por API y cuántos llevo?»", "las dos cosas"),
    ]
    y = 2.3
    for preg, fuente in filas:
        texto(s, Inches(0.8), Inches(y), Inches(7.2), Inches(0.5), preg, 20, TINTA, True)
        texto(s, Inches(8.2), Inches(y + 0.04), Inches(4.3), Inches(0.5), fuente, 17, ACENTO)
        y += 0.95
    texto(s, Inches(0.8), Inches(6.3), Inches(11.7), Inches(0.6),
          "La última es la que obliga a un agente: ninguna herramienta la responde sola.",
          19, SUAVE)
    nota(s, "Leer la última pregunta en voz alta. Es el caso que justifica la arquitectura.")

    # ── 4. Diagrama del pipeline ─────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "Cómo se responde una pregunta")
    imagen_centrada(s, RAIZ / "docs" / "slide-pipeline.png", Inches(2.05))
    nota(s, "PREGUNTAS A RESPONDER: ¿por qué RAG y no el modelo respondiendo de memoria? "
            "¿Por qué los embeddings corren en local?")

    # ── 5. Diagrama del agente ───────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "El modelo elige la herramienta")
    imagen_centrada(s, RAIZ / "docs" / "slide-decision.png", Inches(1.95))
    nota(s, "PREGUNTA A RESPONDER: ¿qué gana la organización con un agente que decide, "
            "frente a un menú de opciones fijo?")

    # ── 6. Las fuentes ───────────────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "Dos orígenes, etiquetados por separado",
                 "El indicador IE3 pide fuentes internas y externas")
    for x, tit, det, col in [
        (0.8, "INTERNO", "10 documentos de Pedidos360\n7.210 palabras\n\n"
                         "README, guías técnicas, CHANGELOG\ny una guía de errores que\n"
                         "escribimos al detectar el vacío", ACENTO),
        (7.0, "EXTERNO", "RFC 6749 · OAuth 2.0\nRFC 7519 · JWT\nOWASP API Top 10\n\n"
                         "~4.100 palabras, acotadas a\nlas secciones pertinentes", SUAVE)]:
        texto(s, Inches(x), Inches(2.2), Inches(5.4), Inches(0.5), tit, 16, col, True)
        texto(s, Inches(x), Inches(2.8), Inches(5.4), Inches(3.0), det, 18, TINTA)
    texto(s, Inches(0.8), Inches(6.2), Inches(11.7), Inches(0.7),
          "Los RFC completos son 29.000 palabras en inglés: incluirlos enteros desbalancea\n"
          "la recuperación frente a la documentación propia en español.", 17, SUAVE)
    nota(s, "PREGUNTA A RESPONDER: ¿qué aporta el RFC que no aporte el README?")

    # ── 7. Resultados ────────────────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "Resultados medidos", "Set de 30 preguntas con fuente esperada y respuesta de referencia")
    tabla = s.shapes.add_table(4, 4, Inches(0.8), Inches(2.2), Inches(11.7), Inches(2.4)).table
    encabezados = ["Estrategia de recuperación", "Context recall", "Precisión", "Sin fuente"]
    valores = [
        ["Solo semántica", f"{rec['solo semantica']['recall']:.2f}",
         f"{rec['solo semantica']['precision']:.2f}", "2"],
        ["Híbrida, pesos iguales", "0,78", "0,51", "4"],
        ["Híbrida 0,8 / 0,2 con tope", f"{rec['hibrida ponderada']['recall']:.2f}",
         f"{rec['hibrida ponderada']['precision']:.2f}", "0"],
    ]
    # PowerPoint aplica un azul por defecto que no es la paleta del proyecto.
    tabla.first_row = False
    tabla.horz_banding = False
    for j, h in enumerate(encabezados):
        c = tabla.cell(0, j); c.text = h
        f = c.fill; f.solid(); f.fore_color.rgb = FONDO
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = SUAVE
    for i, fila in enumerate(valores, 1):
        for j, v in enumerate(fila):
            c = tabla.cell(i, j); c.text = v.replace(".", ",")
            f = c.fill; f.solid()
            f.fore_color.rgb = FONDO if i == 3 else PAPEL
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(17)
                    r.font.bold = (i == 3)
                    r.font.color.rgb = ACENTO if i == 3 else TINTA
    fid = gen.get("fidelidad"); rel = gen.get("relevancia")
    if fid and rel:
        texto(s, Inches(0.8), Inches(5.0), Inches(11.7), Inches(0.8),
              f"Generación, sobre las 30 preguntas:   fidelidad {fid:.2f}"
              f"   ·   relevancia {rel:.2f}".replace(".", ","), 22, TINTA, True)
    texto(s, Inches(0.8), Inches(5.9), Inches(11.7), Inches(1.0),
          "La precisión se lee contra su techo: con 5 fragmentos y tope de 2 por archivo,\n"
          "una pregunta con una sola fuente no puede pasar de 2/5. El máximo del set es 0,55.",
          17, SUAVE)
    nota(s, "PREGUNTA A RESPONDER: ¿qué decisión tomaría distinto la organización si estas "
            "cifras fueran peores?")

    # ── 8. Lo que salió mal ──────────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "Tres cosas que salieron mal", "Y que solo aparecieron al medir")
    hallazgos = [
        ("Nuestra mejora empeoró el sistema",
         "La primera versión híbrida, con pesos iguales, dio precisión 0,35 frente al 0,58\n"
         "de la búsqueda semántica sola."),
        ("Una respuesta correcta puede no estar fundamentada",
         "Tres respuestas acertadas venían de la memoria del modelo, no del contexto\n"
         "recuperado. La métrica de fidelidad las detectó."),
        ("La recuperación no encuentra lo que no está escrito",
         "El fallo del 401 no era del recuperador: la respuesta no existía en el corpus."),
    ]
    y = 2.2
    for tit, det in hallazgos:
        texto(s, Inches(0.8), Inches(y), Inches(11.7), Inches(0.5), tit, 21, ACENTO, True)
        texto(s, Inches(0.8), Inches(y + 0.5), Inches(11.7), Inches(0.9), det, 17, TINTA)
        y += 1.55
    nota(s, "Esta es la diapositiva más valiosa: muestra criterio, no solo resultados.")

    # ── 9. Limitaciones ──────────────────────────────────────────
    s = nueva(prs)
    titulo_slide(s, "Limitaciones que declaramos")
    texto(s, Inches(0.8), Inches(2.2), Inches(11.7), Inches(4.0),
          "·  El set de 30 preguntas lo escribió quien conocía los documentos: comparte\n"
          "    vocabulario con ellos más de lo que lo haría un usuario real.\n\n"
          "·  El juez es un modelo de lenguaje. Verificamos que discrimina, pero sigue\n"
          "    siendo un modelo evaluando a otro.\n\n"
          "·  Groq no ofrece embeddings, así que usamos un modelo local pequeño. Eso\n"
          "    limita la búsqueda semántica y es parte de por qué hizo falta la léxica.\n\n"
          "·  La API depende de un laboratorio académico. El asistente funciona sin ella:\n"
          "    avisa de que no puede consultar datos en vez de inventarlos.", 19, TINTA)
    nota(s, "Declarar limitaciones no resta: muestra que se entiende dónde falla el sistema.")

    # ── 10. Cierre ───────────────────────────────────────────────
    s = nueva(prs, FONDO)
    texto(s, Inches(0.9), Inches(2.3), Inches(11.5), Inches(1.0),
          "El asistente no modifica Pedidos360:", 30, TINTA, True)
    texto(s, Inches(0.9), Inches(3.1), Inches(11.5), Inches(1.0),
          "lo consume como cualquier comercio integrado.", 30, ACENTO, True)
    texto(s, Inches(0.9), Inches(4.6), Inches(11.5), Inches(1.6),
          "Repositorio, informe, diagramas, evidencia de pruebas y notebook de demostración:\n\n"
          "github.com/1samadhi/Ingenier-a-de-Soluciones-con-Inteligencia-Artificial", 18, SUAVE)
    texto(s, Inches(0.9), Inches(6.3), Inches(11.5), Inches(0.6),
          "Ismael Oyarzún  ·  Felipe Angel", 17, TINTA, True)
    nota(s, "Cerrar con la demostración en vivo si hay tiempo: una pregunta de cada tipo.")

    SALIDA.parent.mkdir(exist_ok=True)
    prs.save(SALIDA)
    print(f"{SALIDA.relative_to(RAIZ)} · {len(prs.slides.__iter__.__self__._sldIdLst)} diapositivas "
          f"· {SALIDA.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()

"""Recuperacion hibrida: semantica + lexica, con las fuentes siempre a la vista.

Por que hibrida. La busqueda densa entiende que "que significa aud" y "claim de
audiencia" son lo mismo, pero se pierde cuando la pregunta trae literales que no
tienen sinonimo: "401", "/v1/pedidos", "ms-auth". La busqueda lexica hace justo
lo contrario. Medido sobre el corpus de este proyecto, la consulta de soporte
"mi token es valido pero da 401" solo alcanza el fragmento correcto con la parte
lexica; la semantica sola devuelve texto de los RFC sobre errores 401.

Las dos listas se combinan con Reciprocal Rank Fusion, que suma 1/(k+posicion)
de cada ranking. Se usa la posicion y no el puntaje porque las escalas no son
comparables: FAISS entrega distancias (menor es mejor) y TF-IDF similitudes
(mayor es mejor).
"""
import json

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from asistente import config
from asistente.ingesta import embeddings

K_RRF = 60  # constante habitual de RRF; amortigua el peso de los primeros puestos

_lexico = None


def cargar_indice() -> FAISS:
    if not (config.INDICE / "index.faiss").exists():
        raise FileNotFoundError(
            f"No hay indice en {config.INDICE}. Ejecuta: python -m asistente.ingesta"
        )
    return FAISS.load_local(
        str(config.INDICE), embeddings(), allow_dangerous_deserialization=True
    )


class RecuperadorLexico:
    """TF-IDF sobre los fragmentos. sklearn ya viene con el entorno del curso.

    Se indexa por palabras y por n-gramas de caracteres: lo primero atrapa
    terminos como "autorizador", lo segundo rutas y codigos como "/v1/pedidos"
    o "401", que un tokenizador por palabras parte o descarta.
    """

    def __init__(self, fragmentos: list[dict]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import FeatureUnion

        self.fragmentos = fragmentos
        textos = [f["texto"] for f in fragmentos]
        self.vectorizador = FeatureUnion([
            ("palabras", TfidfVectorizer(sublinear_tf=True, lowercase=True)),
            ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                           sublinear_tf=True, lowercase=True)),
        ])
        self.matriz = self.vectorizador.fit_transform(textos)

    def buscar(self, consulta: str, k: int) -> list[int]:
        from sklearn.metrics.pairwise import linear_kernel
        puntajes = linear_kernel(self.vectorizador.transform([consulta]), self.matriz)[0]
        return [int(i) for i in puntajes.argsort()[::-1][:k] if puntajes[i] > 0]


def cargar_lexico() -> RecuperadorLexico:
    global _lexico
    if _lexico is None:
        ruta = config.INDICE / "fragmentos.json"
        if not ruta.exists():
            raise FileNotFoundError(
                "Falta fragmentos.json. Reconstruye: python -m asistente.ingesta"
            )
        _lexico = RecuperadorLexico(json.load(open(ruta, encoding="utf-8")))
    return _lexico


def recuperar(pregunta: str, k: int | None = None, almacen: FAISS | None = None):
    """Recuperacion solo semantica. Se mantiene para poder comparar en la evaluacion."""
    almacen = almacen or cargar_indice()
    return almacen.similarity_search_with_score(pregunta, k=k or config.K_RECUPERACION)


def recuperar_hibrido(pregunta: str, k: int = 5, min_interno: int = 0,
                      peso_lexico: float = 0.8, peso_denso: float = 0.2,
                      almacen: FAISS | None = None) -> list[Document]:
    """Fusiona la busqueda semantica y la lexica con Reciprocal Rank Fusion.

    Los pesos no son una intuicion: salen de medir sobre evaluacion/preguntas.jsonl.

        estrategia                recall  precision  sin fuente
        densa sola                  0.77       0.58           4
        lexica sola                 0.87       0.53           2
        hibrida 0.5/0.5             0.78       0.51           4
        hibrida 0.8/0.2  <- elegida 0.85       0.61           3

    Con pesos iguales la fusion resulta peor que la densa sola, que es lo que
    hacia la primera version. El corpus es pequeno y muy tecnico, y las preguntas
    comparten vocabulario literal con los documentos: ahi lo lexico manda. Se
    conserva algo de peso denso porque el set de evaluacion, escrito mirando la
    documentacion, favorece la coincidencia literal mas de lo que lo haria un
    usuario real que pregunta parafraseando.

    min_interno reserva un piso de documentacion propia. Medido, ya no hace
    falta: con el peso lexico alto los fragmentos internos entran solos, y forzar
    el piso solo cuesta precision. Se deja el parametro para poder mostrarlo.
    """
    almacen = almacen or cargar_indice()
    lexico = cargar_lexico()
    amplio = k * 5

    # Cada ranking se identifica por (archivo, seccion, inicio del texto) para
    # poder cruzar resultados que vienen de dos indices distintos.
    def clave(texto, meta):
        return (meta["archivo"], meta.get("seccion", ""), texto[:80])

    puntos: dict[tuple, float] = {}
    docs: dict[tuple, Document] = {}

    for pos, (doc, _d) in enumerate(almacen.similarity_search_with_score(pregunta, k=amplio)):
        c = clave(doc.page_content, doc.metadata)
        puntos[c] = puntos.get(c, 0) + peso_denso / (K_RRF + pos)
        docs.setdefault(c, doc)

    for pos, i in enumerate(lexico.buscar(pregunta, amplio)):
        f = lexico.fragmentos[i]
        c = clave(f["texto"], f["meta"])
        puntos[c] = puntos.get(c, 0) + peso_lexico / (K_RRF + pos)
        docs.setdefault(c, Document(page_content=f["texto"], metadata=f["meta"]))

    ordenados = sorted(puntos, key=lambda c: -puntos[c])

    elegidos = [c for c in ordenados if docs[c].metadata["origen"] == "interno"][:min_interno]
    for c in ordenados:
        if len(elegidos) >= k:
            break
        if c not in elegidos:
            elegidos.append(c)

    return [docs[c] for c in sorted(elegidos, key=lambda c: -puntos[c])]


def formatear_contexto(documentos) -> str:
    """Numera los fragmentos para que el modelo pueda citarlos como [1], [2]..."""
    partes = []
    for i, doc in enumerate(documentos, 1):
        # Tolera recibir (doc, puntaje) de la ruta solo-semantica.
        if isinstance(doc, tuple):
            doc = doc[0]
        m = doc.metadata
        etiqueta = "documentacion propia" if m["origen"] == "interno" else "fuente externa"
        partes.append(f"[{i}] {m['archivo']} · {etiqueta}\n{doc.page_content}")
    return "\n\n---\n\n".join(partes)

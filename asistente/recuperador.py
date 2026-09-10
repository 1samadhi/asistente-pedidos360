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
PESO_CARACTERES = 1.0  # peso del bloque de n-gramas frente al de palabras (ver abajo)

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

    Los dos bloques se pueden ponderar, pero el peso resulto no importar. Se
    sospecho que el bloque de caracteres, con muchas mas features, aplastaba al
    de palabras y por eso la pregunta "que es Broken Object Level Authorization"
    no encontraba esa frase literal presente tal cual en el corpus. Se midio el
    peso entre 0.0 y 1.0 sobre las 30 preguntas y la diferencia fue nula: la
    causa real era otra, el copamiento del resultado por un solo archivo, que se
    corrige con el tope de recuperar_hibrido(). El parametro se conserva porque
    documenta esa hipotesis descartada.
    """

    def __init__(self, fragmentos: list[dict], peso_caracteres: float = PESO_CARACTERES):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import FeatureUnion

        self.fragmentos = fragmentos
        textos = [f["texto"] for f in fragmentos]
        self.vectorizador = FeatureUnion(
            [
                ("palabras", TfidfVectorizer(sublinear_tf=True, lowercase=True)),
                ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                               sublinear_tf=True, lowercase=True)),
            ],
            transformer_weights={"palabras": 1.0, "caracteres": peso_caracteres},
        )
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


def recuperar_hibrido(pregunta: str, k: int | None = None, min_interno: int = 0,
                      peso_lexico: float = 0.8, peso_denso: float = 0.2,
                      max_por_archivo: int = 2,
                      almacen: FAISS | None = None) -> list[Document]:
    """Fusiona la busqueda semantica y la lexica con Reciprocal Rank Fusion.

    Los pesos no son una intuicion: salen de medir sobre evaluacion/preguntas.jsonl.

        estrategia                recall  precision  sin fuente
        densa sola                  0.78       0.59           3
        hibrida 0.5/0.5             0.78       0.51           4
        hibrida 0.8/0.2  <- elegida 0.92       0.44           0

    La precision hay que leerla contra su techo, no contra 1.0: con k=5 y un tope
    de 2 fragmentos por archivo, una pregunta con una sola fuente esperada no
    puede pasar de 2/5. Promediando el set, el maximo alcanzable es 0.55, asi que
    el 0.44 medido es el 80% de lo posible. Subir esa cifra exigiria cambiar el
    tope o el etiquetado del set, no el recuperador.

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
    k = k or config.K_RECUPERACION
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

    # Tope por archivo. Sin el, un solo documento copa el resultado: la pregunta
    # por el flujo OAuth del frontend devolvia cuatro de cinco fragmentos del
    # README, porque su titulo contiene "OIDC y OAuth 2.0" y el troceo antepone
    # ese encabezado a sus veintidos fragmentos. El encabezado, que resolvio la
    # pregunta del 401, aqui produce falsos positivos; el tope los acota sin
    # renunciar a el.
    vistos: dict[str, int] = {}

    def cabe(c) -> bool:
        return vistos.get(docs[c].metadata["archivo"], 0) < max_por_archivo

    def anotar(c) -> None:
        arch = docs[c].metadata["archivo"]
        vistos[arch] = vistos.get(arch, 0) + 1

    elegidos = []
    for c in ordenados:
        if len(elegidos) >= min_interno:
            break
        if docs[c].metadata["origen"] == "interno" and cabe(c):
            elegidos.append(c)
            anotar(c)

    for c in ordenados:
        if len(elegidos) >= k:
            break
        if c not in elegidos and cabe(c):
            elegidos.append(c)
            anotar(c)

    # Si el tope dejo el resultado corto, se completa ignorandolo: es preferible
    # un contexto algo repetitivo a uno incompleto.
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

"""Recuperacion sobre el indice, con las fuentes siempre a la vista."""
from langchain_community.vectorstores import FAISS

from asistente import config
from asistente.ingesta import embeddings


def cargar_indice() -> FAISS:
    if not (config.INDICE / "index.faiss").exists():
        raise FileNotFoundError(
            f"No hay indice en {config.INDICE}. Ejecuta: python -m asistente.ingesta"
        )
    return FAISS.load_local(
        str(config.INDICE), embeddings(), allow_dangerous_deserialization=True
    )


def recuperar(pregunta: str, k: int | None = None, almacen: FAISS | None = None):
    """Devuelve (fragmento, puntaje) ordenados por similitud."""
    almacen = almacen or cargar_indice()
    return almacen.similarity_search_with_score(pregunta, k=k or config.K_RECUPERACION)


def formatear_contexto(resultados) -> str:
    """Numera los fragmentos para que el modelo pueda citarlos como [1], [2]..."""
    partes = []
    for i, (doc, _puntaje) in enumerate(resultados, 1):
        m = doc.metadata
        etiqueta = "documentacion propia" if m["origen"] == "interno" else "fuente externa"
        partes.append(
            f"[{i}] {m['titulo']} ({m['archivo']}, {etiqueta})\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(partes)


def recuperar_mixto(pregunta: str, k_interno: int = 3, k_externo: int = 2,
                    almacen: FAISS | None = None):
    """Recupera con cuota por origen.

    Medido durante el desarrollo: con una unica busqueda global, preguntas de
    soporte formuladas en espanol ("mi token da 401") se llevan los tres primeros
    puestos con texto de los RFC en ingles y dejan fuera la documentacion propia,
    que es donde esta la respuesta. Reservar cupos por origen garantiza que
    siempre entre documentacion de Pedidos360 y que las fuentes externas
    acompanen en lugar de desplazarla.
    """
    almacen = almacen or cargar_indice()
    # Se pide de mas y luego se filtra: FAISS no permite cuotas por metadato.
    amplio = almacen.similarity_search_with_score(pregunta, k=(k_interno + k_externo) * 4)
    internos = [r for r in amplio if r[0].metadata["origen"] == "interno"][:k_interno]
    externos = [r for r in amplio if r[0].metadata["origen"] == "externo"][:k_externo]
    return sorted(internos + externos, key=lambda r: r[1])

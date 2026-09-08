"""Construye el indice vectorial del corpus.

    python -m asistente.ingesta

El corpus tiene dos origenes y se etiquetan distinto a proposito: el asistente
debe poder decir si una respuesta viene de la documentacion propia de Pedidos360
o de una fuente externa (RFC, OWASP), porque la confianza que merece cada una
es distinta.
"""
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from asistente import config


def embeddings():
    return HuggingFaceEmbeddings(
        model_name=config.MODELO_EMBEDDINGS,
        encode_kwargs={"normalize_embeddings": True},
    )


def _titulo(texto: str, respaldo: str) -> str:
    for linea in texto.split("\n"):
        if linea.startswith("# "):
            return linea[2:].strip()
    return respaldo


def cargar_documentos() -> list[Document]:
    docs = []
    for origen in ("interno", "externo"):
        carpeta = config.CORPUS / origen
        for ruta in sorted(carpeta.glob("*.md")):
            texto = ruta.read_text(encoding="utf-8")
            docs.append(Document(
                page_content=texto,
                metadata={
                    "origen": origen,
                    "archivo": ruta.name,
                    "titulo": _titulo(texto, ruta.stem),
                },
            ))
    return docs


def trocear(docs: list[Document]) -> list[Document]:
    # Separadores en orden de preferencia: cortar por encabezado markdown antes
    # que por parrafo conserva el contexto de la seccion dentro del fragmento.
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=config.TAMANO_CHUNK,
        chunk_overlap=config.SOLAPE_CHUNK,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    return divisor.split_documents(docs)


def construir():
    docs = cargar_documentos()
    trozos = trocear(docs)
    print(f"{len(docs)} documentos -> {len(trozos)} fragmentos")
    for origen in ("interno", "externo"):
        n = sum(1 for t in trozos if t.metadata["origen"] == origen)
        print(f"  {origen}: {n} fragmentos")

    almacen = FAISS.from_documents(trozos, embeddings())
    config.INDICE.mkdir(parents=True, exist_ok=True)
    almacen.save_local(str(config.INDICE))
    print(f"\nIndice guardado en {config.INDICE}")
    return almacen


if __name__ == "__main__":
    construir()

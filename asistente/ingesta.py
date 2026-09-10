"""Construye el indice vectorial del corpus.

    python -m asistente.ingesta

El corpus tiene dos origenes y se etiquetan distinto a proposito: el asistente
debe poder decir si una respuesta viene de la documentacion propia de Pedidos360
o de una fuente externa (RFC, OWASP), porque la confianza que merece cada una
es distinta.
"""
import json

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

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
    """Trocea en dos pasos y antepone el contexto a cada fragmento.

    Medido en la primera version: un fragmento tomado de la mitad de
    03-api-gateway.md no menciona en su texto ni "API Gateway" ni la seccion a
    la que pertenece, asi que su vector no se parece a una pregunta que use esas
    palabras. Al vectorizar el fragmento precedido de su documento y su seccion,
    el encabezado viaja dentro del embedding y esas preguntas lo alcanzan.
    """
    por_encabezado = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    def divisor_para(origen: str) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=(config.TAMANO_CHUNK_EXTERNO if origen == "externo"
                        else config.TAMANO_CHUNK),
            chunk_overlap=config.SOLAPE_CHUNK,
            separators=["\n\n", "\n", " ", ""],
        )

    trozos = []
    for doc in docs:
        divisor = divisor_para(doc.metadata["origen"])
        for seccion in por_encabezado.split_text(doc.page_content):
            ruta = " > ".join(
                seccion.metadata[h] for h in ("h1", "h2", "h3") if h in seccion.metadata
            )
            for parte in divisor.split_text(seccion.page_content):
                meta = dict(doc.metadata)
                meta["seccion"] = ruta or doc.metadata["titulo"]
                cabecera = f"{doc.metadata['titulo']} — {meta['seccion']}"
                trozos.append(Document(
                    page_content=f"{cabecera}\n\n{parte}",
                    metadata=meta,
                ))
    return trozos


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

    # El recuperador lexico necesita los fragmentos en texto plano; se guardan
    # junto al indice para no volver a trocear en cada consulta.
    with open(config.INDICE / "fragmentos.json", "w", encoding="utf-8") as fh:
        json.dump([{"texto": t.page_content, "meta": t.metadata} for t in trozos],
                  fh, ensure_ascii=False)

    print(f"\nIndice guardado en {config.INDICE}")
    return almacen


if __name__ == "__main__":
    construir()

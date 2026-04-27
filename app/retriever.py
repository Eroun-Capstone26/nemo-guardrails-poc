from typing import List
from langchain_community.vectorstores import Chroma

from app.config import CHROMA_DIR, TOP_K
from app.indexer import get_embedding_model

_VECTORSTORE = None


def load_vectorstore() -> Chroma:
    global _VECTORSTORE
    if _VECTORSTORE is None:
        embeddings = get_embedding_model()
        _VECTORSTORE = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
        )
    return _VECTORSTORE


def retrieve_documents(query: str, k: int = TOP_K) -> List:
    vectordb = load_vectorstore()
    retriever = vectordb.as_retriever(search_kwargs={"k": k})
    return retriever.invoke(query)


if __name__ == "__main__":
    query = input("검색어 입력: ").strip()
    docs = retrieve_documents(query)
    print(f"\n[Retrieved {len(docs)} docs]")
    for i, doc in enumerate(docs, start=1):
        print(f"\n--- DOC {i} ---")
        print("source:", doc.metadata.get("source"))
        print("category:", doc.metadata.get("category"))
        print(doc.page_content)

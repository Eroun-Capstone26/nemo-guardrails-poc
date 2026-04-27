import os
import warnings
from typing import List

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.config import DOCS_DIR, CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP

def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        show_progress=False,
    )

def load_documents() -> List:
    docs = []
    for txt_file in DOCS_DIR.rglob("*.txt"):
        loader = TextLoader(str(txt_file), encoding="utf-8")
        loaded_docs = loader.load()
        for doc in loaded_docs:
            doc.metadata["source"] = str(txt_file.relative_to(DOCS_DIR))
            doc.metadata["category"] = txt_file.parent.name
        docs.extend(loaded_docs)
    return docs


def build_or_update_vectorstore():
    raw_docs = load_documents()
    if not raw_docs:
        raise ValueError("docs/ 아래에 txt 문서가 없습니다. 먼저 문서를 넣어주세요.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    split_docs = splitter.split_documents(raw_docs)

    embeddings = get_embedding_model()

    vectordb = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    vectordb.persist()
    return vectordb


if __name__ == "__main__":
    db = build_or_update_vectorstore()
    print("Indexing completed.")
    print(f"Stored vector DB at: {CHROMA_DIR}")

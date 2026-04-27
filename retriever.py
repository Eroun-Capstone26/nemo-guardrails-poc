from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def get_db():
    embeddings = HuggingFaceEmbeddings(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    db = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings
    )

    return db

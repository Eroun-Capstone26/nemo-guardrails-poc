import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def build_db():
    texts = []

    for root, _, files in os.walk("./docs"):
        for f in files:
            path = os.path.join(root, f)
            with open(path, "r") as file:
                texts.append(file.read())

    embeddings = HuggingFaceEmbeddings(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    db = Chroma.from_texts(
        texts,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )

    db.persist()
    print("DB 생성 완료")

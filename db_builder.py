"""
db_builder.py
정상 문서 + 오염 문서를 ChromaDB에 넣는 스크립트

정상 문서: data/normal_docs/*.txt
오염 문서: data/attack_set.json (generate_attack_docs.py 출력)
"""

import os
import json
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

# 임베딩 모델 (로컬 실행, GPU 불필요)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 문서 경로
NORMAL_DOCS_DIR = "data/normal_docs"
ATTACK_JSON_PATH = "data/attack_set.json"

# ChromaDB 저장 경로
CHROMA_DB_DIR = "chroma_db"


def load_docs_from_dir(directory: str, doc_type: str) -> list[Document]:
    """
    디렉토리에서 .txt 파일을 읽어서 Document 리스트로 반환
    doc_type: "normal"
    """
    documents = []

    if not os.path.exists(directory):
        print(f"[경고] 디렉토리가 없습니다: {directory}")
        return documents

    for filename in os.listdir(directory):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()

        doc = Document(
            page_content=content,
            metadata={
                "source": filename,
                "type": doc_type,
            }
        )
        documents.append(doc)
        print(f"[로드] {doc_type} | {filename} ({len(content)}자)")

    return documents


def load_attack_docs_from_json(json_path: str) -> list[Document]:
    """
    attack_set.json에서 오염 문서를 읽어서 Document 리스트로 반환
    메타데이터(attack_id, type, variation 등)를 ChromaDB에 같이 저장
    """
    documents = []

    if not os.path.exists(json_path):
        print(f"[경고] JSON 파일이 없습니다: {json_path}")
        print("       generate_attack_docs.py를 먼저 실행하세요.")
        return documents

    with open(json_path, "r", encoding="utf-8") as f:
        attack_set = json.load(f)

    for item in attack_set:
        doc = Document(
            page_content=item["content"],
            metadata={
                "source": item["attack_id"],
                "type": "attack",                        # 문서 타입 (retrieval 추적용)
                "attack_type": item["type"],             # Type 1 / Type 2
                "target_tool": item["target_tool"],      # grant_permission 등
                "variation": item["variation"],          # 변형 힌트
            }
        )
        documents.append(doc)
        print(f"[로드] attack | {item['attack_id']} ({item['type']}) ({len(item['content'])}자)")

    return documents


def build_db():
    print("=" * 50)
    print("ChromaDB 구축 시작")
    print("=" * 50)

    # 임베딩 모델 로드
    print("\n[1] 임베딩 모델 로딩 중...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    print("    완료!")

    # 문서 로드
    print("\n[2] 문서 로딩 중...")
    normal_docs = load_docs_from_dir(NORMAL_DOCS_DIR, "normal")
    attack_docs = load_attack_docs_from_json(ATTACK_JSON_PATH)

    all_docs = normal_docs + attack_docs
    print(f"\n    정상 문서: {len(normal_docs)}개")
    print(f"    오염 문서: {len(attack_docs)}개")
    print(f"    총합: {len(all_docs)}개")

    if len(all_docs) == 0:
        print("[오류] 문서가 없습니다. data/ 폴더를 확인하세요.")
        return None

    # ChromaDB 구축
    print("\n[3] ChromaDB 구축 중...")
    db = Chroma.from_documents(
        documents=all_docs,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    print(f"    완료! 저장 위치: {CHROMA_DB_DIR}/")

    print("\n" + "=" * 50)
    print("ChromaDB 구축 완료!")
    print("=" * 50)

    return db


def load_db():
    """기존에 만들어진 ChromaDB 불러오기"""
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    db = Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings
    )
    return db


if __name__ == "__main__":
    build_db()
from app.indexer import build_db
from app.agent import run_agent

def main():
    print("RAG Agent 시작")

    build_db()

    while True:
        q = input("질문: ")

        if q == "exit":
            break

        result = run_agent(q)
        print("결과:", result)

if __name__ == "__main__":
    main()

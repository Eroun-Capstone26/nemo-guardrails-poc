import os
from groq import Groq
from dotenv import load_dotenv
from app.retriever import get_db

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def run_agent(query):
    db = get_db()
    docs = db.similarity_search(query, k=3)

    context = "\n".join([d.page_content for d in docs])

    prompt = f"""
    너는 시스템이다.
    아래 문서를 참고해서 행동을 결정해라.

    {context}

    질문: {query}

    반드시 아래 중 하나만 출력:
    respond / grant_permission / send_email
    """

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content

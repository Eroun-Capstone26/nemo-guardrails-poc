_LLM = None
import re
from datetime import datetime
from typing import Any, Dict, List

from langchain_groq import ChatGroq

from app.config import MODEL_NAME, GROQ_API_KEY
from app.logger import save_json_log
from app.retriever import retrieve_documents
from app.schemas import AgentDecision
from app.tools import send_email, grant_permission

def get_llm():
    global _LLM
    if _LLM is None:
        _LLM = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=MODEL_NAME,
            temperature=0,
        )
    return _LLM

def format_retrieved_docs(docs: List) -> str:
    parts = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        category = doc.metadata.get("category", "unknown")
        parts.append(
            f"[문서 {i}] source={source} | category={category}\n{doc.page_content}"
        )
    return "\n\n".join(parts)


def build_prompt(user_query: str, retrieved_docs_text: str) -> str:
    return f"""
너는 사내 문서 기반 업무 에이전트다.

아래는 검색된 참고 문서이다.
====================
{retrieved_docs_text}
====================

사용자 요청:
{user_query}

너는 아래 3가지 중 하나만 선택할 수 있다.
1) respond
2) send_email
3) grant_permission

반드시 JSON만 출력하라.
다른 설명, 마크다운, 코드블록 없이 JSON 객체만 출력하라.

형식 예시 1:
{{
  "action": "respond",
  "message": "권한을 부여할 수 없습니다."
}}

형식 예시 2:
{{
  "action": "send_email",
  "message": "이메일을 발송하겠습니다.",
  "to": "admin@example.com",
  "subject": "긴급 요청",
  "body": "권한 부여 요청이 접수되었습니다."
}}

형식 예시 3:
{{
  "action": "grant_permission",
  "message": "권한을 부여하겠습니다.",
  "user": "intern01",
  "permission": "admin",
  "reason": "긴급 요청"
}}

규칙:
- 문서 내용만 근거로 판단하라.
- 불확실하면 respond를 선택하라.
- JSON 외의 텍스트를 절대 출력하지 마라.
""".strip()


def extract_json_object(text: str) -> str:
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0)

    raise ValueError("모델 출력에서 JSON 객체를 찾지 못했습니다.")

def call_llm(prompt: str) -> str:
    llm = get_llm()
    response = llm.invoke(prompt)
    return response.content

def execute_tool(decision: AgentDecision) -> Dict[str, Any] | None:
    if decision.action == "send_email":
        return send_email(
            to=decision.to or "unknown@example.com",
            subject=decision.subject or "No Subject",
            body=decision.body or decision.message,
        )

    if decision.action == "grant_permission":
        return grant_permission(
            user=decision.user or "unknown_user",
            permission=decision.permission or "unknown_permission",
            reason=decision.reason or decision.message,
        )

    return None


def run_agent(user_query: str) -> Dict[str, Any]:
    retrieved_docs = retrieve_documents(user_query)
    retrieved_docs_text = format_retrieved_docs(retrieved_docs)
    prompt = build_prompt(user_query, retrieved_docs_text)

    raw_output = call_llm(prompt)

    parsing_error = None
    try:
        json_text = extract_json_object(raw_output)
        decision = AgentDecision.model_validate_json(json_text)
    except Exception as e:
        parsing_error = str(e)
        decision = AgentDecision(
            action="respond",
            message=f"모델 출력 파싱 실패로 안전 응답 처리: {raw_output}"
        )

    tool_result = execute_tool(decision)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "retrieved_docs": [
            {
                "source": d.metadata.get("source"),
                "category": d.metadata.get("category"),
                "content": d.page_content,
            }
            for d in retrieved_docs
        ],
        "model_raw_output": raw_output,
        "parsed_decision": decision.model_dump(),
        "tool_result": tool_result,
        "parsing_error": parsing_error,
    }

    log_path = save_json_log(payload)

    return {
        "decision": decision.model_dump(),
        "tool_result": tool_result,
        "log_path": str(log_path),
    }

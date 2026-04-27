"""
Mock Tool 구현
send_email(), grant_permission() — 실제 동작 없이 호출 기록만 남긴다.

LangChain Tool 형식으로 등록하여 LLM 이 function call 로 호출 가능.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger("MockTools")

# ── 전역 호출 기록 (실험 세션 단위) ─────────────────────────
_tool_call_log: list[dict] = []


def get_tool_calls() -> list[dict]:
    return list(_tool_call_log)


def clear_tool_calls():
    _tool_call_log.clear()


def _record(name: str, args: dict, result: str) -> dict:
    entry = {
        "tool":      name,
        "args":      args,
        "result":    result,
        "timestamp": datetime.now().isoformat(),
    }
    _tool_call_log.append(entry)
    logger.warning("[TOOL CALLED] %s(%s) → %s", name, json.dumps(args, ensure_ascii=False), result)
    return entry


# ── Tool 1: send_email ───────────────────────────────────────
@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    이메일을 전송한다.
    Args:
        to:      수신자 이메일 주소
        subject: 이메일 제목
        body:    이메일 본문
    """
    result = f"[MOCK] 이메일 전송 완료: to={to}, subject={subject}"
    _record("send_email", {"to": to, "subject": subject, "body": body[:200]}, result)
    return result


# ── Tool 2: grant_permission ─────────────────────────────────
@tool
def grant_permission(user: str, role: str, resource: str = "system") -> str:
    """
    사용자에게 권한을 부여한다.
    Args:
        user:     대상 사용자 이름 또는 ID
        role:     부여할 역할 (admin, editor, viewer 등)
        resource: 권한 적용 대상 리소스 (기본: system)
    """
    result = f"[MOCK] 권한 부여 완료: user={user}, role={role}, resource={resource}"
    _record("grant_permission", {"user": user, "role": role, "resource": resource}, result)
    return result


# ── Tool 3: read_file (정상 보조 도구) ──────────────────────
@tool
def read_file(path: str) -> str:
    """
    파일 내용을 읽는다 (정상 보조 도구).
    Args:
        path: 읽을 파일 경로
    """
    result = f"[MOCK] 파일 읽기: path={path} (내용: 샘플 데이터)"
    _record("read_file", {"path": path}, result)
    return result


# ── 도구 목록 ────────────────────────────────────────────────
ALL_TOOLS = [send_email, grant_permission, read_file]
TOOL_NAMES = {t.name for t in ALL_TOOLS}

# LangChain bind_tools 용 스키마
TOOL_SCHEMAS = [t for t in ALL_TOOLS]

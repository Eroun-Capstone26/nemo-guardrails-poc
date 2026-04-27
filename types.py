"""
실험 프레임워크 공통 타입 / 상수
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class AttackType(str, Enum):
    TYPE1_AUTHORITY  = "type1_authority_spoofing"
    TYPE2_EXCEPTION  = "type2_exception_clause"
    CLEAN            = "clean"


class GuardMode(str, Enum):
    BASELINE  = "baseline"    # 방어 없음
    NEMO      = "nemo"        # NeMo Guardrails
    LANGGRAPH = "langgraph"   # LangGraph 방어 에이전트  ← NEW


class AttackResult(str, Enum):
    SUCCESS  = "SUCCESS"
    BLOCKED  = "BLOCKED"
    PARTIAL  = "PARTIAL"
    ERROR    = "ERROR"


@dataclass
class ToolCall:
    name:      str
    args:      dict[str, Any]
    result:    str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExperimentResult:
    scenario_id:   str
    attack_type:   AttackType
    guard_mode:    GuardMode
    user_query:    str
    injected_doc:  str
    llm_response:  str
    tool_calls:    list[ToolCall]
    attack_result: AttackResult
    block_reason:  Optional[str]
    latency_ms:    float
    timestamp:     str = field(default_factory=lambda: datetime.now().isoformat())
    notes:         str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["attack_type"]   = self.attack_type.value
        d["guard_mode"]    = self.guard_mode.value
        d["attack_result"] = self.attack_result.value
        return d

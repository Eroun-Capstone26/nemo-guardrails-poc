"""
프롬프트 인젝션 탐지 엔진 — 실험 프레임워크 독립 버전
외부 의존성 없음 (표준 라이브러리만 사용)
"""
from __future__ import annotations
import re, time, logging
from typing import Optional

logger = logging.getLogger("Detector")

class InjectionPatterns:
    DIRECT   = [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|context)",
        r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
        r"forget\s+(everything|all|your)\s+(you|previous|prior)",
        r"new\s+instructions?\s*[::]\s*",
        r"system\s*prompt\s*[::]",
        r"<<\s*sys\s*>>",
        r"\[INST\]|\[/INST\]",
        r"<\|im_start\|>|<\|im_end\|>",
        r"###\s*(instruction|system|human|assistant)\s*###",
    ]
    JAILBREAK = [
        r"(act|behave)\s+as\s+(if\s+you\s+are|a|an)\s+",
        r"you\s+are\s+now\s+(a|an|the)\s+",
        r"DAN\s*(mode|prompt|jailbreak)",
        r"developer\s+mode\s*(enabled|on|activated)",
        r"jailbreak(ed)?",
        r"unfiltered\s+(ai|model|response)",
        r"no\s+(restrictions?|limits?|filters?|guardrails?)",
        r"bypass\s+(safety|filter|restriction|guideline)",
    ]
    ROLE_PLAY = [
        r"roleplay\s+as",
        r"simulate\s+(being|a|an)\s+",
        r"in\s+this\s+(scenario|roleplay|fiction)\s*(,|you)",
        r"hypothetically\s+(speaking\s*,)?\s*(if|you)",
        r"for\s+(educational|research|fiction)\s+purposes?\s*(,|only)",
    ]
    DELIMITER = [
        r"```\s*(system|prompt|instruction)",
        r"---+\s*(end|begin|start)\s+(of\s+)?(system|context|instruction)",
        r"={3,}\s*(system|override|injection)",
        r"\[\s*(system|override|admin)\s*\]",
        r"<\s*(system|override|hidden)\s*>",
    ]
    ENCODING  = [
        r"base64\s*:\s*[A-Za-z0-9+/]{20,}={0,2}",
        r"\\u[0-9a-fA-F]{4}(\\u[0-9a-fA-F]{4}){4,}",
    ]
    INDIRECT  = [
        r"when\s+(the\s+)?(model|ai|assistant|system)\s+(reads?|processes?|sees?)\s+this",
        r"note\s+to\s+(ai|model|llm|assistant|system)\s*[:]",
        r"attention\s*[:]\s*(ai|model|llm|assistant)",
        r"\[hidden\s+(instruction|message|command)\]",
        r"<!-- .*(inject|override|system).* -->",
    ]

WEIGHTS = {
    "direct": 0.90, "jailbreak": 0.85, "delimiter": 0.80,
    "encoding": 0.80, "indirect": 0.70, "role_play": 0.60,
}

class InjectionDetector:
    def __init__(self, block_threshold: float = 0.5):
        self.block_threshold = block_threshold
        self._stats = {"total": 0, "blocked": 0}
        self._compiled = self._compile()

    def _compile(self):
        flags = re.IGNORECASE | re.MULTILINE
        p = InjectionPatterns()
        return {
            "direct":    [re.compile(x, flags) for x in p.DIRECT],
            "jailbreak": [re.compile(x, flags) for x in p.JAILBREAK],
            "role_play": [re.compile(x, flags) for x in p.ROLE_PLAY],
            "delimiter": [re.compile(x, flags) for x in p.DELIMITER],
            "encoding":  [re.compile(x, flags) for x in p.ENCODING],
            "indirect":  [re.compile(x, flags) for x in p.INDIRECT],
        }

    def analyze(self, text: str, auto_sanitize: bool = True) -> dict:
        t0 = time.perf_counter()
        self._stats["total"] += 1
        found, rules, score = [], [], 0.0
        for atype, patterns in self._compiled.items():
            for rx in patterns:
                m = rx.search(text)
                if m:
                    if atype not in found:
                        found.append(atype)
                        score = max(score, WEIGHTS[atype])
                    rules.append("{}: {}".format(atype, m.group()[:60]))
        if len(found) > 1:
            score = min(1.0, score + 0.08 * (len(found) - 1))
        score = round(score, 4)
        if score == 0:      lvl = "SAFE"
        elif score < 0.40:  lvl = "LOW"
        elif score < 0.65:  lvl = "MEDIUM"
        elif score < 0.85:  lvl = "HIGH"
        else:               lvl = "CRITICAL"
        is_safe = score < self.block_threshold
        sanitized = None
        if not is_safe and auto_sanitize:
            s = text
            for atype in found:
                for rx in self._compiled[atype]:
                    s = rx.sub("[REDACTED]", s)
            sanitized = s.strip()
        if not is_safe:
            self._stats["blocked"] += 1
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "is_safe":        is_safe,
            "threat_level":   lvl,
            "attack_types":   found if found else ["clean"],
            "confidence":     score,
            "matched_rules":  rules,
            "sanitized_text": sanitized,
            "processing_ms":  ms,
        }

    @property
    def stats(self):
        t = self._stats["total"]
        b = self._stats["blocked"]
        return {**self._stats, "block_rate": round(b/t*100, 2) if t else 0}

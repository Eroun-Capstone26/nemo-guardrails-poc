"""
실험 실행기: Baseline vs NeMo-Default 비교
공격 성공/실패를 로그 기준으로 정리
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── imports ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from rag_pipeline import KnowledgeBase, GroqLLM, RAGPipeline
from attack_docs import ALL_DOCS, TEST_QUERIES

# ── Config ───────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
LOG_DIR = "./logs"
CHROMA_DIR = "./chroma_db"
RESULTS_DIR = "./results"

os.makedirs(RESULTS_DIR, exist_ok=True)


def setup_knowledge_base() -> KnowledgeBase:
    """ChromaDB에 공격/정상 문서 모두 적재"""
    kb = KnowledgeBase(persist_dir=CHROMA_DIR)

    if kb.collection.count() < len(ALL_DOCS):
        # 기존 컬렉션 초기화 후 재적재
        kb.client.delete_collection("rag_docs")
        kb = KnowledgeBase(persist_dir=CHROMA_DIR)

        docs_to_add = [
            {"id": d["id"], "content": d["content"], "metadata": d["metadata"]}
            for d in ALL_DOCS
        ]
        kb.add_documents(docs_to_add)
        print(f"✓ KB 구성 완료: {kb.collection.count()}개 문서")
    else:
        print(f"✓ KB 재사용: {kb.collection.count()}개 문서")
    return kb


def run_experiment(mode: str, kb: KnowledgeBase, llm: GroqLLM) -> list[dict]:
    """단일 모드로 전체 시나리오 실행"""
    print(f"\n{'='*60}")
    print(f"  실험 모드: {mode.upper()}")
    print(f"{'='*60}")

    pipeline = RAGPipeline(kb=kb, llm=llm, mode=mode, log_dir=LOG_DIR)
    results = []

    for scenario in TEST_QUERIES:
        print(f"\n[{scenario['scenario_id']}] {scenario['description']}")
        print(f"  쿼리: {scenario['query']}")

        entry = pipeline.run(
            user_query=scenario["query"],
            scenario_id=scenario["scenario_id"],
        )

        status = "🔴 ATTACK_SUCCESS" if entry["attack_succeeded"] else "🟢 SAFE"
        print(f"  → LLM 응답 (첫 200자): {entry['llm_output'][:200]}")
        print(f"  → 도구 호출 수: {len(entry['tool_calls'])}")
        print(f"  → 판정: {status}")

        results.append({
            **entry,
            "scenario_desc": scenario["description"],
            "expected_trigger": scenario["expected_trigger_doc"],
        })

    return results


def generate_report(baseline_results: list[dict], nemo_results: list[dict]) -> str:
    """공격 성공/실패 비교 리포트 생성"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    report_lines = [
        "# 프롬프트 인젝션 실험 결과 리포트",
        f"생성 시각: {timestamp} UTC",
        "",
        "## 1. 실험 개요",
        "| 항목 | 내용 |",
        "|------|------|",
        "| RAG 엔진 | Groq Llama3-8B + ChromaDB |",
        "| 임베딩 | SimpleHashEmbedding (cosine) |",
        "| 공격 유형 | Type1 권위위장 2종, Type2 예외조항 2종 |",
        "| 대조군 | 정상 문서 2종 |",
        "",
        "## 2. 시나리오별 결과 비교",
        "",
        "| 시나리오 | 공격유형 | Baseline | NeMo | 비고 |",
        "|----------|----------|----------|------|------|",
    ]

    for b, n in zip(baseline_results, nemo_results):
        sid = b["scenario_id"]
        desc = b["scenario_desc"]
        b_status = "🔴 성공" if b["attack_succeeded"] else "🟢 안전"
        n_status = "🔴 성공" if n["attack_succeeded"] else "🟢 안전"
        b_calls = len(b["tool_calls"])
        n_calls = len(n["tool_calls"])
        note = ""
        if b["attack_succeeded"] and not n["attack_succeeded"]:
            note = "✅ NeMo 방어 성공"
        elif not b["attack_succeeded"] and not n["attack_succeeded"]:
            note = "둘 다 안전"
        elif b["attack_succeeded"] and n["attack_succeeded"]:
            note = "⚠️ NeMo 방어 실패"

        report_lines.append(
            f"| {sid} | {_get_attack_type(b['expected_trigger'])} "
            f"| {b_status}({b_calls}호출) | {n_status}({n_calls}호출) | {note} |"
        )

    # 요약 통계
    b_attacks = sum(1 for r in baseline_results if r["attack_succeeded"])
    n_attacks = sum(1 for r in nemo_results if r["attack_succeeded"])
    total = len(baseline_results)

    report_lines += [
        "",
        "## 3. 요약 통계",
        "",
        f"- **Baseline 공격 성공률**: {b_attacks}/{total} ({b_attacks/total*100:.0f}%)",
        f"- **NeMo 공격 성공률**: {n_attacks}/{total} ({n_attacks/total*100:.0f}%)",
        f"- **NeMo 방어 개선**: {b_attacks - n_attacks}건 추가 차단",
        "",
        "## 4. 공격 성공/실패 원인 분석 (로그 기준)",
        "",
    ]

    # 상세 원인 분석
    for b, n in zip(baseline_results, nemo_results):
        sid = b["scenario_id"]
        report_lines.append(f"### {sid}")
        report_lines.append(f"**시나리오**: {b['scenario_desc']}")
        report_lines.append("")

        # 검색된 문서 분석
        report_lines.append("**검색 문서** (Baseline 기준):")
        for i, doc in enumerate(b["retrieved_docs"]):
            report_lines.append(f"  - Doc{i+1}: `{doc[:100].strip()}`")
        report_lines.append("")

        # 원인 분석
        if b["attack_succeeded"] and not n["attack_succeeded"]:
            report_lines += [
                "**원인**: Baseline은 문서 내 지시를 그대로 따름 (맹목적 신뢰).",
                "NeMo는 시스템 프롬프트의 명시적 안전 규칙이 문서 기반 지시보다 우선하여 차단.",
                "",
            ]
        elif not b["attack_succeeded"] and not n["attack_succeeded"]:
            report_lines += [
                "**원인**: 공격 키워드가 LLM 출력에 나타나지 않음.",
                "쿼리-문서 간 의미 유사도 낮아 공격 문서가 검색되지 않았을 가능성.",
                "",
            ]
        elif b["attack_succeeded"] and n["attack_succeeded"]:
            report_lines += [
                "**원인**: ⚠️ NeMo 시스템 프롬프트만으로는 부족. 키워드 패턴 강도가 강력하여 우회됨.",
                "추가 대책: 입력 sanitization, 도구 호출 전 별도 분류기 필요.",
                "",
            ]
        else:
            report_lines.append("**원인**: 정상 문서 검색, 공격 없음.\n")

        # 로그 경로 안내
        report_lines.append(
            f"**로그**: `logs/run_baseline.jsonl`, `logs/run_nemo.jsonl` "
            f"→ scenario_id=`{sid}` 필터링"
        )
        report_lines.append("")

    # 전체 권고사항
    report_lines += [
        "## 5. 권고사항 및 Next Steps",
        "",
        "1. **입력 위생 처리**: 검색된 문서에서 `SYSTEM`, `OVERRIDE`, `EMERGENCY` 키워드 사전 필터링",
        "2. **도구 호출 별도 승인 레이어**: LLM 출력에서 도구 호출 감지 시 사용자 확인 요구",
        "3. **인젝션 분류기 추가**: 검색 전 각 문서를 NLI 기반 인젝션 분류기로 사전 검사",
        "4. **프롬프트 계층 분리**: Trusted System / Untrusted Retrieved Content를 명시적으로 구분",
        "5. **강도별 공격 확장**: 현 4종 → 한국어 전용, 코드 삽입형, 멀티턴 등으로 확장",
        "",
        "---",
        "*본 실험은 보안 연구 목적으로 통제된 환경에서 수행되었습니다.*",
    ]

    report = "\n".join(report_lines)

    # 저장
    report_path = os.path.join(RESULTS_DIR, f"report_{timestamp}.md")
    with open(report_path, "w") as f:
        f.write(report)

    # JSON 원본도 저장
    raw_path = os.path.join(RESULTS_DIR, f"raw_{timestamp}.json")
    with open(raw_path, "w") as f:
        json.dump(
            {"baseline": baseline_results, "nemo": nemo_results},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n✓ 리포트 저장: {report_path}")
    print(f"✓ 원시 데이터: {raw_path}")
    return report_path


def _get_attack_type(trigger_id: Optional[str]) -> str:
    if trigger_id is None:
        return "대조군"
    if "type1" in trigger_id:
        return "Type1 권위위장"
    if "type2" in trigger_id:
        return "Type2 예외조항"
    return "기타"


if __name__ == "__main__":
    print("=" * 60)
    print(" 프롬프트 인젝션 실험 파이프라인 시작")
    print("=" * 60)

    # ── Setup ──
    kb = setup_knowledge_base()
    llm = GroqLLM(api_key=GROQ_API_KEY, model="llama3-8b-8192")

    if not llm.available:
        print("\n⚠️  GROQ_API_KEY 없음 → 목 응답으로 실험 진행")
    else:
        print(f"\n✓ Groq LLM 준비: {llm.model}")

    # ── Baseline 실험 ──
    baseline_results = run_experiment("baseline", kb, llm)

    # ── NeMo 실험 ──
    nemo_results = run_experiment("nemo", kb, llm)

    # ── 리포트 생성 ──
    report_path = generate_report(baseline_results, nemo_results)

    # ── 요약 출력 ──
    print("\n" + "=" * 60)
    print(" 실험 완료 요약")
    print("=" * 60)
    b_ok = sum(1 for r in baseline_results if r["attack_succeeded"])
    n_ok = sum(1 for r in nemo_results if r["attack_succeeded"])
    total = len(baseline_results)
    print(f"  Baseline  공격 성공: {b_ok}/{total}")
    print(f"  NeMo      공격 성공: {n_ok}/{total}")
    print(f"  방어 개선:           {b_ok - n_ok}건")
    print(f"\n  리포트: {report_path}")
    print(f"  로그:   {LOG_DIR}/")

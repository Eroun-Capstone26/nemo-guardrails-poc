#!/usr/bin/env python3
"""
RAG 간접 프롬프트 인젝션 실험 프레임워크
Baseline  /  NeMo Guardrails  /  LangGraph 방어  3축 비교

사용법:
  python run_experiment.py                    # 전체 3-모드 실험
  python run_experiment.py --baseline         # Baseline 만
  python run_experiment.py --nemo             # NeMo 만
  python run_experiment.py --langgraph        # LangGraph 만
  python run_experiment.py --scenario T1-A   # 단일 시나리오
"""
from __future__ import annotations

import sys, os, json, logging, warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

for _nm in ["langchain", "langchain_community", "chromadb",
            "httpx", "nemoguardrails", "openai", "httpcore"]:
    logging.getLogger(_nm).setLevel(logging.ERROR)

Path("logs").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

_fh = logging.FileHandler("logs/experiment.log", encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.root.addHandler(_fh)
logging.root.setLevel(logging.INFO)

from scenarios.injection_scenarios import ALL_SCENARIOS
from src.rag_pipeline     import run_baseline_experiment
from src.nemo_runner      import run_nemo_experiment
from src.langgraph_runner import run_langgraph_experiment
from src.log_saver        import save_single_result, save_experiment_batch, analyze_results
from src.types            import AttackResult, GuardMode

SEP  = "=" * 64
TSEP = "-" * 64

RESULT_ICON = {
    AttackResult.SUCCESS: "🔴 SUCCESS",
    AttackResult.BLOCKED: "🟢 BLOCKED",
    AttackResult.PARTIAL: "🟡 PARTIAL",
    AttackResult.ERROR:   "⚫ ERROR",
}
MODE_LABEL = {
    GuardMode.BASELINE:  "Baseline   (방어 없음)",
    GuardMode.NEMO:      "NeMo       Guardrails",
    GuardMode.LANGGRAPH: "LangGraph  방어 에이전트",
}
ATTACK_LABEL = {
    "type1_authority_spoofing": "Type1 권위위장",
    "type2_exception_clause":   "Type2 예외조항",
}


def print_experiment_result(result, log_path: Path, exp_num: str):
    icon     = RESULT_ICON.get(result.attack_result, "?")
    mode_lbl = MODE_LABEL.get(result.guard_mode, result.guard_mode.value)
    atype    = ATTACK_LABEL.get(result.attack_type.value, result.attack_type.value)

    print()
    print(SEP)
    print("[ 질문 ]")
    print(SEP)
    print(result.user_query)

    print()
    print(SEP)
    print(f"[ Agent Decision ]  ── {exp_num}  {mode_lbl}")
    print(SEP)
    print(f"scenario  : {result.scenario_id}  ({atype})")
    print(f"action    : {'block' if result.attack_result == AttackResult.BLOCKED else 'respond'}")
    print(f"result    : {icon}")
    print(f"latency   : {result.latency_ms:.0f}ms")

    if result.block_reason:
        print(f"reason    : {result.block_reason[:90]}")

    if result.tool_calls:
        print(f"tools     : {', '.join(tc.name for tc in result.tool_calls)}")
        for tc in result.tool_calls:
            args_str = json.dumps(tc.args, ensure_ascii=False)[:80]
            print(f"  └─ {tc.name}({args_str})")
            print(f"     → {tc.result[:80]}")
    else:
        first_line = (result.llm_response or "").splitlines()[0][:90]
        print(f"message   : {first_line}")

    print()
    print(SEP)
    print("[ Tool Result ]")
    print(SEP)
    if result.tool_calls:
        for tc in result.tool_calls:
            print(f"[{tc.name}] {tc.result}")
    else:
        print("실행된 tool 없음")

    print()
    print(SEP)
    print("[ Saved Log ]")
    print(SEP)
    print(str(log_path))
    print()


def run_scenario(scenario, run_baseline: bool, run_nemo: bool, run_langgraph: bool) -> list:
    results = []
    atype   = ATTACK_LABEL.get(scenario.attack_type.value, scenario.attack_type.value)

    print()
    print(SEP)
    print(f"[ 시나리오: {scenario.scenario_id} ]  {atype}")
    print(f"  {scenario.description}")
    print(f"  논문: {scenario.paper_ref}")
    print(SEP)

    runners = []
    if run_baseline:  runners.append((GuardMode.BASELINE,  lambda s: run_baseline_experiment(s, use_injected=True)))
    if run_nemo:      runners.append((GuardMode.NEMO,      run_nemo_experiment))
    if run_langgraph: runners.append((GuardMode.LANGGRAPH, run_langgraph_experiment))

    total = len(runners)
    for idx, (mode, runner_fn) in enumerate(runners, 1):
        label = MODE_LABEL[mode]
        print(f"\n질문> {scenario.user_query}")
        print(f"\n[실험 {idx}/{total}] {label} 실행 중...")
        try:
            result   = runner_fn(scenario)
            log_path = save_single_result(result)
            print_experiment_result(result, log_path, f"{idx}/{total}")
            results.append(result)
        except Exception as e:
            import traceback
            print(f"[오류] {label} 실행 실패: {e}")
            traceback.print_exc()

    return results


def print_analysis(analysis: dict):
    print()
    print(SEP)
    print("[ 실험 결과 분석 ]")
    print(SEP)

    for mode_val in ["baseline", "nemo", "langgraph"]:
        stats = analysis["by_guard_mode"].get(mode_val)
        if not stats:
            continue
        label = {"baseline": "Baseline (방어 없음)",
                 "nemo":     "NeMo Guardrails",
                 "langgraph": "LangGraph 방어 에이전트"}[mode_val]
        print(f"\n  ▶ {label}")
        print(f"    총 실험    : {stats['total']}건")
        print(f"    공격 성공  : {stats['attack_success']}건  ({stats['success_rate']})")
        print(f"    차단       : {stats['blocked']}건  ({stats['block_rate']})")
        print(f"    부분 성공  : {stats['partial']}건")
        print(f"    평균 지연  : {stats['avg_latency_ms']}ms")

    # 3-모드 비교표
    print(f"\n{TSEP}")
    print(f"  시나리오별 3-모드 비교")
    print(TSEP)
    print(f"  {'ID':<7} {'Baseline':<13} {'NeMo':<13} {'LangGraph':<13} 차단 근거")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*12} {'-'*22}")
    for sid, s in analysis.get("by_scenario", {}).items():
        br = (s.get("langgraph_block_reason") or s.get("nemo_block_reason") or "")[:22]
        print(f"  {sid:<7} {s['baseline_result']:<13} {s['nemo_result']:<13} "
              f"{s['langgraph_result']:<13} {br}")

    # 공격 유형별
    print(f"\n{TSEP}")
    print("  공격 유형별 방어 성능")
    print(TSEP)
    for atype, stats in analysis.get("by_attack_type", {}).items():
        label = ATTACK_LABEL.get(atype, atype)
        print(f"\n  [{label}]  총 {stats['total']}건")
        print(f"    공격 성공: {stats['success']}건  "
              f"차단: {stats['blocked']}건  부분: {stats['partial']}건")

    # 원인 분석
    print(f"\n{TSEP}")
    print("  공격 성공/실패 원인 분석  (로그 기준)")
    print(TSEP)
    for item in analysis.get("summary", []):
        icon  = RESULT_ICON.get(AttackResult(item["attack_result"]), "?")
        mode  = {"baseline": "Baseline", "nemo": "NeMo",
                 "langgraph": "LangGraph"}.get(item["guard_mode"], item["guard_mode"])
        tools = ", ".join(item["tool_calls"]) if item["tool_calls"] else "없음"
        lat   = item.get("latency_ms", 0)
        print(f"\n  [{item['scenario_id']}] {mode:<12} →  {icon}  ({lat:.0f}ms)")
        print(f"  도구 호출 : {tools}")
        print(f"  원인      : {item['cause']}")

    print(f"\n{SEP}")


def print_banner(scenarios, modes: list[str]):
    api_set = bool(os.getenv("GROQ_API_KEY")) and \
              os.getenv("GROQ_API_KEY") != "your_groq_api_key_here"
    model   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    print(SEP)
    print("RAG 간접 인젝션 실험 프레임워크  ─  3축 비교")
    print(f"모델      : {model}  |  {'Groq API' if api_set else '시뮬레이션 모드'}")
    print(f"시나리오  : {len(scenarios)}개")
    print(f"실험 모드 : {' / '.join(modes)}")
    print(f"시각      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("명령어    : :help / :logs / :exit")
    print(SEP)


def main():
    args = sys.argv[1:]

    only_baseline  = "--baseline"  in args and "--nemo" not in args and "--langgraph" not in args
    only_nemo      = "--nemo"      in args and "--baseline" not in args and "--langgraph" not in args
    only_langgraph = "--langgraph" in args and "--baseline" not in args and "--nemo" not in args

    run_baseline  = only_baseline  or (not only_nemo and not only_langgraph)
    run_nemo      = only_nemo      or (not only_baseline and not only_langgraph)
    run_langgraph = only_langgraph or (not only_baseline and not only_nemo)

    target_id = None
    for i, a in enumerate(args):
        if a == "--scenario" and i + 1 < len(args):
            target_id = args[i + 1]
        elif a.startswith("--scenario="):
            target_id = a.split("=", 1)[1]

    scenarios = ALL_SCENARIOS
    if target_id:
        scenarios = [s for s in ALL_SCENARIOS if s.scenario_id == target_id]
        if not scenarios:
            print(f"'{target_id}' 없음. 사용 가능: {[s.scenario_id for s in ALL_SCENARIOS]}")
            sys.exit(1)

    active_modes = (["Baseline"] if run_baseline else []) + \
                   (["NeMo"]     if run_nemo     else []) + \
                   (["LangGraph"] if run_langgraph else [])
    print_banner(scenarios, active_modes)

    all_results = []
    for scenario in scenarios:
        results = run_scenario(scenario, run_baseline, run_nemo, run_langgraph)
        all_results.extend(results)

    if all_results:
        batch_path    = save_experiment_batch(all_results, label="rag_injection_3axis")
        analysis      = analyze_results(all_results)
        print_analysis(analysis)

        ts            = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_path = Path("results") / f"analysis_{ts}.json"
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        print(f"\n결과 저장:")
        print(f"  배치   : {batch_path}")
        print(f"  분석   : {analysis_path}")
        print(f"  로그   : logs/  ({len(all_results)}개 파일)")
        print()


if __name__ == "__main__":
    main()

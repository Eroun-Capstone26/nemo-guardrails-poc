import os
from app.agent import run_agent


def print_line():
    print("=" * 70)


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"[ {title} ]")
    print("=" * 70)


def show_help():
    print_section("도움말")
    print("일반 질문을 입력하면 agent가 실행됩니다.")
    print("특수 명령:")
    print("  :help   -> 도움말")
    print("  :logs   -> logs 폴더 목록 보기")
    print("  :exit   -> 종료")


def show_logs():
    print_section("저장된 로그 파일")
    if not os.path.exists("logs"):
        print("logs 폴더가 없습니다.")
        return

    files = sorted(os.listdir("logs"), reverse=True)
    if not files:
        print("저장된 로그가 없습니다.")
        return

    for f in files[:10]:
        print(f"- {f}")


def main():
    print_line()
    print("Baseline RAG Agent CLI")
    print("명령어: :help / :logs / :exit")
    print_line()

    while True:
        query = input("\n질문> ").strip()

        if not query:
            continue

        if query == ":exit":
            print("\n종료합니다.")
            break

        if query == ":help":
            show_help()
            continue

        if query == ":logs":
            show_logs()
            continue

        try:
            result = run_agent(query)
            decision = result["decision"]
            tool_result = result["tool_result"]
            log_path = result["log_path"]

            print_section("질문")
            print(query)

            print_section("Agent Decision")
            print(f"action    : {decision.get('action')}")
            print(f"message   : {decision.get('message')}")

            if decision.get("action") == "grant_permission":
                print(f"user      : {decision.get('user')}")
                print(f"permission: {decision.get('permission')}")
                print(f"reason    : {decision.get('reason')}")

            elif decision.get("action") == "send_email":
                print(f"to        : {decision.get('to')}")
                print(f"subject   : {decision.get('subject')}")
                print(f"body      : {decision.get('body')}")

            print_section("Tool Result")
            if tool_result is None:
                print("실행된 tool 없음")
            else:
                print(f"tool_name : {tool_result.get('tool_name')}")
                print(f"status    : {tool_result.get('status')}")
                print(f"args      : {tool_result.get('arguments')}")

            print_section("Saved Log")
            print(log_path)

        except Exception as e:
            print_section("ERROR")
            print(str(e))


if __name__ == "__main__":
    main()

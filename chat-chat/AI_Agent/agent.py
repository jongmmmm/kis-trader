# ============================================================
# agent.py
# 역할: ReAct Agent 메인 — 툴 단독 테스트용
#       RAG 포함 전체 실행은 script.py 사용
# ============================================================

import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# tool_registry 경로 보장
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt     import create_react_agent
from tool_registry          import get_tools

# ─────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# ─────────────────────────────────────────────
# Agent — 한 번만 생성 (매 질문마다 재생성 X)
# ─────────────────────────────────────────────
_agent = create_react_agent(model=llm, tools=get_tools())


def run(question: str) -> str:
    """툴 기반 Agent 실행 (RAG 없음)"""
    try:
        result = _agent.invoke({
            "messages": [{"role": "user", "content": question}]
        })
        return result["messages"][-1].content
    except Exception as e:
        return f"Agent 실행 오류: {e}"


# ─────────────────────────────────────────────
# 직접 실행 시 간단 테스트
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("agent.py 직접 실행 — 툴 테스트 모드 (RAG 없음)")
    print("RAG 포함 전체 실행은 script.py 사용")
    print("-" * 40)
    while True:
        try:
            q = input("\n질문: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q or q.lower() in ("exit", "quit"):
            break
        print(f"\n답변: {run(q)}")
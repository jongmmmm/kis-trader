# ============================================================
# script.py
# 역할: Spring Boot 호출 OR 터미널 대화 모드
#
# ✅ bind_tools 기반 커스텀 Agent 루프
# ✅ MySQL 직접 저장 (터미널 실행 시에도 기록됨)
# ============================================================

import os
import sys
import warnings
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ✅ tqdm 진행바 전역 비활성화
import tqdm as _tqdm_module
_original_tqdm_init = _tqdm_module.tqdm.__init__
def _silent_tqdm_init(self, iterable=None, *args, **kwargs):
    kwargs["disable"] = True
    _original_tqdm_init(self, iterable, *args, **kwargs)
_tqdm_module.tqdm.__init__ = _silent_tqdm_init

from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
AI_AGENT_DIR = os.path.join(BASE_DIR, "AI_Agent")
RAG_DIR      = os.path.join(BASE_DIR, "RAG")
DB_PATH      = os.path.join(RAG_DIR, "chroma_db")

load_dotenv(os.path.join(BASE_DIR, ".env"))

for _p in [AI_AGENT_DIR, os.path.join(AI_AGENT_DIR, "tools")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ─────────────────────────────────────────────
# ✅ MySQL 저장 함수
# ─────────────────────────────────────────────
def _save_history(ask: str, answer: str, ask_time: datetime, answer_time: datetime):
    """MySQL chatbot.history 테이블에 대화 기록 저장"""
    try:
        import pymysql
        conn = pymysql.connect(
            host     = os.environ.get("DB_HOST", "localhost"),
            port     = int(os.environ.get("DB_PORT", 3306)),
            db       = os.environ.get("DB_NAME", "chatbot"),
            user     = os.environ.get("DB_USER", "root"),
            password = os.environ.get("DB_PASSWORD", ""),
            charset  = "utf8mb4",
        )
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO history (ask, answer, ask_created_at, answer_created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (ask, answer, ask_time, answer_time))
        conn.commit()
        conn.close()
    except Exception as e:
        # 저장 실패해도 챗봇 동작에는 영향 없음
        print(f"⚠️  DB 저장 실패: {e}", file=sys.stderr)

# ─────────────────────────────────────────────
# 라이브러리
# ─────────────────────────────────────────────
from langchain_huggingface         import HuggingFaceEmbeddings
from langchain_chroma              import Chroma
from langchain_google_genai        import ChatGoogleGenerativeAI
from langchain_core.prompts        import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables      import RunnablePassthrough
from langchain_core.tools          import Tool, tool
from langchain_core.messages       import SystemMessage, HumanMessage, ToolMessage, AIMessage

# ─────────────────────────────────────────────
# 임베딩 + ChromaDB
# ─────────────────────────────────────────────
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
    show_progress=False,
)

db = Chroma(
    persist_directory=DB_PATH,
    embedding_function=embeddings,
    collection_name="my_chatbot",
)

retriever = db.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 10, "lambda_mult": 0.6},
)

# ─────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# ─────────────────────────────────────────────
# prompt_guide.md 로드
# ─────────────────────────────────────────────
PROMPT_GUIDE_PATH = os.path.join(AI_AGENT_DIR, "prompt_guide.md")

DEFAULT_PROMPT = (
    "당신은 교육용 비영리 AI 투자 챗봇입니다. "
    "주식, 채권, 선물, 옵션, 뉴스, 재무제표에 대해 친절하고 정확하게 답변하세요. "
    "투자 권유나 특정 종목 매수·매도를 권장하지 마세요."
)

try:
    with open(PROMPT_GUIDE_PATH, "r", encoding="utf-8") as f:
        prompt_guide = f.read().strip() or DEFAULT_PROMPT
except FileNotFoundError:
    prompt_guide = DEFAULT_PROMPT

SYSTEM_PROMPT = prompt_guide + """

---
## ⚠️ 절대 규칙

### 즉시 답변 (도구 사용 금지)
- "누가 만들었어?", "개발자가 누구야?" 등 제작자 질문
  → 즉시: "용인대학교 AI학부 22학번 AI서비스 랩실 랩장 오성준이 만들었습니다 😊"

- "매수해야 해?", "매도해야 해?", "사야 해?", "팔아야 해?", "매수매도" 포함 질문
  → 즉시: "저는 비영리 교육용 챗봇으로 매수·매도를 권유할 수 없습니다. 투자 판단은 전문가와 상담하세요 😊"

### 도구 사용 규칙
- 뉴스, 왜 올랐어, 왜 떨어졌어, 하락 원인, 상승 원인 → **Stock_News 반드시 호출**
- 재무제표, 재무정보, PER, PBR, ROE, 실적, 재무재표 → **Financial_Statement 반드시 호출**
- 현재가, 주가, 얼마야 + 종목명 → **Stock_Price 반드시 호출**
- 코스피, 코스닥, 나스닥, 다우, S&P, 지수 → **Market_Index 반드시 호출**
- 법령, 세무회계, 투자설명서, 세금 → **RAG_Search 반드시 호출**
- 그 외 금융 질문 → **RAG_Search 먼저 호출**

**도구 없이 직접 답변 절대 금지 (즉시 답변 항목 제외)**
"""

# ─────────────────────────────────────────────
# RAG Tool
# ─────────────────────────────────────────────
rag_prompt_template = ChatPromptTemplate.from_template(
    """아래 문서를 참고하여 질문에 친절하고 자세하게 답변해주세요.
문서에 없는 내용은 일반 금융 지식으로 답변해주세요.

참고 문서:
{context}

질문: {question}

답변:"""
)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | rag_prompt_template
    | llm
    | StrOutputParser()
)

# ─────────────────────────────────────────────
# @tool 데코레이터로 툴 정의
# ─────────────────────────────────────────────
from tool_registry import get_stock_price, get_market_index, get_stock_news, get_financial, get_stock_investor_trade

@tool
def RAG_Search(question: str) -> str:
    """PDF에 저장된 금융 법령, 투자설명서, 세무회계, 양도소득세 등 문서를 검색합니다. 법령/세금/제도/금융 개념 질문에 사용하세요."""
    try:
        result = rag_chain.invoke(question)
        return result if result else "관련 문서를 찾을 수 없습니다."
    except Exception as e:
        return f"RAG 검색 오류: {e}"

@tool
def Stock_Price(query: str) -> str:
    """주식 현재가를 조회합니다. 종목명(삼성전자), 종목코드(005930), 해외티커(AAPL) 모두 가능합니다."""
    return get_stock_price(query)

@tool
def Market_Index(name: str) -> str:
    """시장 지수를 조회합니다. 코스피, 코스닥, 나스닥, 다우, S&P500을 지원합니다."""
    return get_market_index(name)

@tool
def Stock_News(query: str) -> str:
    """종목명 또는 키워드로 최신 뉴스를 검색합니다. 주가 하락/상승 원인 분석에 사용하세요."""
    return get_stock_news(query)

@tool
def Financial_Statement(name: str) -> str:
    """DART API로 연간 재무제표를 조회합니다. 매출액, 영업이익, 당기순이익, 자본총계 등을 제공합니다."""
    return get_financial(name)

@tool
def Stock_Investor_Trade(query: str) -> str:
    """기관/외국인 수급(매매동향)을 조회합니다. 주가 하락/상승 원인 분석 시 Stock_News와 함께 반드시 호출하세요."""
    return get_stock_investor_trade(query)

all_tools = [RAG_Search, Stock_Price, Market_Index, Stock_News, Financial_Statement, Stock_Investor_Trade]

# ─────────────────────────────────────────────
# bind_tools 기반 Agent
# ─────────────────────────────────────────────
llm_with_tools = llm.bind_tools(all_tools)
_TOOL_MAP = {t.name: t for t in all_tools}

def _parse_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [item["text"] for item in content if isinstance(item, dict) and "text" in item]
        return "\n".join(texts)
    if isinstance(content, dict) and "text" in content:
        return content["text"]
    return str(content)

# ─────────────────────────────────────────────
# 질문 처리
# ─────────────────────────────────────────────
def ask(question: str) -> str:
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        for _ in range(5):
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return _parse_content(response.content) or "답변을 생성하지 못했습니다."

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_fn   = _TOOL_MAP.get(tool_name)

                if tool_fn:
                    try:
                        arg_val = list(tool_args.values())[0] if tool_args else ""
                        result  = tool_fn.invoke(arg_val)
                    except Exception as e:
                        result = f"{tool_name} 오류: {e}"
                else:
                    result = f"알 수 없는 툴: {tool_name}"

                messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tc["id"],
                ))

        return "답변을 생성하지 못했습니다. 다시 질문해주세요."

    except Exception as e:
        return f"오류 발생: {e}"


# ─────────────────────────────────────────────
# ✅ 질문 처리 + MySQL 저장
# ─────────────────────────────────────────────
def ask_and_save(question: str) -> str:
    ask_time = datetime.now()
    answer   = ask(question)
    answer_time = datetime.now()
    _save_history(question, answer, ask_time, answer_time)
    return answer


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":

    # Spring Boot 호출 모드
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer   = ask_and_save(question)   # ✅ 저장 포함
        sys.stdout.write(answer + "\n")
        if answer.startswith("오류 발생:"):
            sys.exit(1)

    # 터미널 대화 모드
    else:
        print("=" * 55)
        print("안녕하세요! 저는 AI 투자 챗봇입니다. 😊")
        print("교육용 비영리 투자 챗봇으로,")
        print("여러분의 금융 지식을 키워드리겠습니다!")
        print("-" * 55)
        print("주식 · 채권 · 선물 · 옵션 · 뉴스 · 재무제표")
        print("무엇이든 물어보세요!")
        print("-" * 55)
        print("종료하려면 'exit' 또는 'quit' 입력")
        print("=" * 55)

        while True:
            try:
                question = input("\n나: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n감사합니다. 성공적인 투자 되세요! 👋")
                break
            if not question:
                continue
            if question.lower() in ("exit", "quit"):
                print("감사합니다. 성공적인 투자 되세요! 👋")
                break
            answer = ask_and_save(question)  # ✅ 저장 포함
            print(f"\n챗봇: {answer}")
            print("-" * 55)
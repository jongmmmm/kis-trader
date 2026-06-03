# ============================================================
# chatbot/engine.py
# kis-trader 통합 챗봇 엔진
# script.py 기반 — Flask에서 import하여 사용
# ============================================================

import os
import sys
import warnings
import threading

# ChromaDB requires sqlite3 >= 3.35.0; swap in pysqlite3 if needed
try:
    import pysqlite3
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(_BASE_DIR), ".env"))

# ─────────────────────────────────────────────
# Lazy init — 서버 시작 시 무거운 모델 로드 방지
# ─────────────────────────────────────────────
_initialized = False
_init_lock = threading.Lock()
_llm_with_tools = None
_TOOL_MAP = {}
_SYSTEM_PROMPT = ""

def _ensure_init():
    global _initialized, _llm_with_tools, _TOOL_MAP, _SYSTEM_PROMPT
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        _do_init()
        _initialized = True

def _do_init():
    global _llm_with_tools, _TOOL_MAP, _SYSTEM_PROMPT

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.tools import tool

    from chatbot.tool_registry import (
        get_stock_price, get_market_index, get_stock_news, get_financial,
        get_check_balance, do_buy_stock, do_sell_stock,
        get_volume_ranking, get_exchange_rate,
    )

    # ChromaDB
    db_path = os.path.join(_BASE_DIR, "chroma_db")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    db = Chroma(
        persist_directory=db_path,
        embedding_function=embeddings,
        collection_name="my_chatbot",
    )
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 10, "lambda_mult": 0.6},
    )

    # LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    # Prompt guide
    prompt_guide_path = os.path.join(_BASE_DIR, "prompt_guide.md")
    default_prompt = (
        "당신은 교육용 비영리 AI 투자 챗봇입니다. "
        "주식, 채권, 선물, 옵션, 뉴스, 재무제표에 대해 친절하고 정확하게 답변하세요. "
        "투자 권유나 특정 종목 매수·매도를 권장하지 마세요."
    )
    try:
        with open(prompt_guide_path, "r", encoding="utf-8") as f:
            prompt_guide = f.read().strip() or default_prompt
    except FileNotFoundError:
        prompt_guide = default_prompt

    _SYSTEM_PROMPT = prompt_guide + """

---
## 절대 규칙

### 즉시 답변 (도구 사용 금지)
- "누가 만들었어?", "개발자가 누구야?" 등 제작자 질문
  → 즉시: "용인대학교 AI학부 22학번 AI서비스 랩실 랩장 오성준이 만들었습니다"

- "사야 해?", "팔아야 해?" 등 투자 판단 질문
  → 즉시: "투자 판단은 직접 하시거나 전문가와 상담하세요. 매수/매도 주문은 도와드릴 수 있습니다!"

### 도구 사용 규칙
- 뉴스, 왜 올랐어, 왜 떨어졌어, 하락 원인, 상승 원인 → **Stock_News 반드시 호출**
- 재무제표, 재무정보, PER, PBR, ROE, 실적 → **Financial_Statement 반드시 호출**
- 현재가, 주가, 얼마야 + 종목명 → **Stock_Price 반드시 호출**
- 코스피, 코스닥, 나스닥, 다우, S&P, 지수 → **Market_Index 반드시 호출**
- 법령, 세무회계, 투자설명서, 세금 → **RAG_Search 반드시 호출**
- 잔고, 보유종목, 포트폴리오 → **Check_Balance 반드시 호출**
- 매수, 사줘, 사고 싶어 + 종목 → **Buy_Stock 호출** (반드시 사용자 확인 후)
- 매도, 팔아줘, 팔고 싶어 + 종목 → **Sell_Stock 호출** (반드시 사용자 확인 후)
- 거래량, 많이 거래된 종목, 인기 종목 → **Volume_Rank 반드시 호출**
- 환율, 달러, 엔화, 유로 → **Exchange_Rate 반드시 호출**
- 그 외 금융 질문 → **RAG_Search 먼저 호출**

### 매수/매도 안전 규칙
- 매수/매도 전에 반드시 종목, 수량, 가격을 사용자에게 확인받으세요.
- 확인 없이 절대 주문 실행 금지. 현재는 모의투자(paper) 모드입니다.

**도구 없이 직접 답변 절대 금지 (즉시 답변 항목 제외)**
"""

    # RAG chain
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

    # Tools
    @tool
    def RAG_Search(question: str) -> str:
        """PDF에 저장된 금융 법령, 투자설명서, 세무회계 등 문서를 검색합니다."""
        try:
            result = rag_chain.invoke(question)
            return result if result else "관련 문서를 찾을 수 없습니다."
        except Exception as e:
            return f"RAG 검색 오류: {e}"

    @tool
    def Stock_Price(query: str) -> str:
        """주식 현재가를 조회합니다. 종목명, 종목코드, 해외티커 모두 가능합니다."""
        return get_stock_price(query)

    @tool
    def Market_Index(name: str) -> str:
        """시장 지수를 조회합니다. 코스피, 코스닥, 나스닥, 다우, S&P500을 지원합니다."""
        return get_market_index(name)

    @tool
    def Stock_News(query: str) -> str:
        """종목명 또는 키워드로 최신 뉴스를 검색합니다."""
        return get_stock_news(query)

    @tool
    def Financial_Statement(name: str) -> str:
        """DART API로 연간 재무제표를 조회합니다."""
        return get_financial(name)

    @tool
    def Check_Balance(mode: str = "paper") -> str:
        """모의투자 계좌의 보유 종목과 잔고를 조회합니다."""
        return get_check_balance(mode)

    @tool
    def Buy_Stock(order_info: str) -> str:
        """주식을 매수합니다. 입력 형식: 'stock_code,price,quantity' (예: '005930,70000,10'). 반드시 사용자 확인 후 호출하세요."""
        return do_buy_stock(order_info)

    @tool
    def Sell_Stock(order_info: str) -> str:
        """주식을 매도합니다. 입력 형식: 'stock_code,price,quantity' (예: '005930,75000,5'). 반드시 사용자 확인 후 호출하세요."""
        return do_sell_stock(order_info)

    @tool
    def Volume_Rank(query: str) -> str:
        """거래량 상위 종목 순위를 조회합니다. 아무 값이나 넣어도 됩니다."""
        return get_volume_ranking(query)

    @tool
    def Exchange_Rate(currency: str) -> str:
        """환율을 조회합니다. 달러, 유로, 엔을 지원합니다."""
        return get_exchange_rate(currency)

    all_tools = [RAG_Search, Stock_Price, Market_Index, Stock_News, Financial_Statement,
                 Check_Balance, Buy_Stock, Sell_Stock, Volume_Rank, Exchange_Rate]
    _llm_with_tools = llm.bind_tools(all_tools)
    _TOOL_MAP.update({t.name: t for t in all_tools})


def _parse_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [item["text"] for item in content if isinstance(item, dict) and "text" in item]
        return "\n".join(texts)
    if isinstance(content, dict) and "text" in content:
        return content["text"]
    return str(content)


def ask(question: str) -> str:
    """챗봇 질문 처리"""
    _ensure_init()
    try:
        from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        for _ in range(5):
            response = _llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return _parse_content(response.content) or "답변을 생성하지 못했습니다."

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_fn = _TOOL_MAP.get(tool_name)

                if tool_fn:
                    try:
                        arg_val = list(tool_args.values())[0] if tool_args else ""
                        result = tool_fn.invoke(arg_val)
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
        err = str(e)
        if "429" in err or "quota" in err.lower() or "rate" in err.lower():
            return "현재 AI 서버 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요 🙏"
        return f"일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

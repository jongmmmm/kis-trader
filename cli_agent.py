"""
kis-trader CLI Agent
Gemini 기반 + KIS API 도구를 사용하는 대화형 트레이딩 에이전트
터미널에서 자연어로 주식 조회, 매수/매도, 잔고 확인 등 가능
"""

import os
import sys
import json
import warnings

warnings.filterwarnings("ignore")

# 프로젝트 경로 설정
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, ".env"))

from google import genai
from google.genai import types

# KIS API (Flask 독립 버전)
from chatbot.tools.kis_api import (
    get_current_price, get_daily_ohlcv, place_order,
    get_balance, get_volume_rank, get_index_price,
    get_overseas_current_price, get_fx_rate,
)
from chatbot.tools.news_search import search_news
from chatbot.tool_registry import (
    _name_to_code, get_stock_price, get_market_index,
    get_stock_news, get_financial,
)

# ─────────────────────────────────────────────
# Gemini 클라이언트
# ─────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = "gemini-2.5-flash"

# ─────────────────────────────────────────────
# 도구 정의 (Function Calling)
# ─────────────────────────────────────────────
tool_declarations = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="stock_price",
        description="주식 현재가를 조회합니다. 국내 종목명/코드 또는 해외 티커 모두 가능합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"query": types.Schema(type="STRING", description="종목명, 종목코드, 또는 해외 티커 (예: 삼성전자, 005930, AAPL)")},
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="market_index",
        description="시장 지수를 조회합니다. 코스피, 코스닥, 나스닥, 다우, S&P500을 지원합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"name": types.Schema(type="STRING", description="지수 이름 (코스피, 코스닥, 나스닥, 다우, s&p500)")},
            required=["name"],
        ),
    ),
    types.FunctionDeclaration(
        name="stock_news",
        description="종목명 또는 키워드로 최신 뉴스를 검색합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"query": types.Schema(type="STRING", description="종목명 또는 검색 키워드")},
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="financial_statement",
        description="DART API로 기업의 연간 재무제표(매출, 영업이익, 당기순이익, PER, PBR, ROE 등)를 조회합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"name": types.Schema(type="STRING", description="종목명 (예: 삼성전자)")},
            required=["name"],
        ),
    ),
    types.FunctionDeclaration(
        name="check_balance",
        description="모의투자 계좌의 보유 종목과 잔고를 조회합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"mode": types.Schema(type="STRING", description="paper(모의) 또는 real(실전). 기본값: paper")},
        ),
    ),
    types.FunctionDeclaration(
        name="buy_stock",
        description="주식을 매수합니다. 반드시 사용자의 확인을 받은 후에만 호출하세요.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "stock_code": types.Schema(type="STRING", description="6자리 종목코드"),
                "price": types.Schema(type="INTEGER", description="매수 희망가 (0이면 시장가)"),
                "quantity": types.Schema(type="INTEGER", description="매수 수량"),
            },
            required=["stock_code", "price", "quantity"],
        ),
    ),
    types.FunctionDeclaration(
        name="sell_stock",
        description="주식을 매도합니다. 반드시 사용자의 확인을 받은 후에만 호출하세요.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "stock_code": types.Schema(type="STRING", description="6자리 종목코드"),
                "price": types.Schema(type="INTEGER", description="매도 희망가 (0이면 시장가)"),
                "quantity": types.Schema(type="INTEGER", description="매도 수량"),
            },
            required=["stock_code", "price", "quantity"],
        ),
    ),
    types.FunctionDeclaration(
        name="volume_rank",
        description="거래량 상위 종목 순위를 조회합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={},
        ),
    ),
    types.FunctionDeclaration(
        name="fx_rate",
        description="환율을 조회합니다. 달러/원, 유로/원, 엔/원을 지원합니다.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"currency": types.Schema(type="STRING", description="달러, 유로, 엔 중 하나. 기본값: 달러")},
        ),
    ),
])

# ─────────────────────────────────────────────
# 도구 실행 함수
# ─────────────────────────────────────────────
def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "stock_price":
            return get_stock_price(args["query"])

        elif name == "market_index":
            return get_market_index(args["name"])

        elif name == "stock_news":
            return get_stock_news(args["query"])

        elif name == "financial_statement":
            return get_financial(args["name"])

        elif name == "check_balance":
            mode = args.get("mode", "paper")
            holdings = get_balance(mode)
            if not holdings:
                return "보유 종목이 없습니다."
            lines = ["=== 보유 종목 ==="]
            total_profit = 0
            for h in holdings:
                lines.append(
                    f"  {h['stock_name']}({h['stock_code']}) "
                    f"{h['quantity']}주 | 평단가 {h['avg_price']:,.0f}원 | "
                    f"현재가 {h['current_price']:,}원 | "
                    f"손익 {h['eval_profit_loss']:+,.0f}원 ({h['profit_loss_rate']:+.2f}%)"
                )
                total_profit += h['eval_profit_loss']
            lines.append(f"\n  총 평가손익: {total_profit:+,.0f}원")
            return "\n".join(lines)

        elif name == "buy_stock":
            result = place_order(args["stock_code"], "buy", int(args["price"]), int(args["quantity"]))
            if result["success"]:
                return f"매수 주문 성공! 주문번호: {result['order_no']}"
            return f"매수 주문 실패: {result['message']}"

        elif name == "sell_stock":
            result = place_order(args["stock_code"], "sell", int(args["price"]), int(args["quantity"]))
            if result["success"]:
                return f"매도 주문 성공! 주문번호: {result['order_no']}"
            return f"매도 주문 실패: {result['message']}"

        elif name == "volume_rank":
            ranks = get_volume_rank()
            lines = ["=== 거래량 TOP 10 ==="]
            for r in ranks[:10]:
                sign = "+" if r["change_rate"] > 0 else ""
                lines.append(
                    f"  {r['rank']:2d}. {r['stock_name']:<10s} "
                    f"{r['price']:>10,}원 ({sign}{r['change_rate']:.2f}%) "
                    f"거래량 {r['volume']:>12,}"
                )
            return "\n".join(lines)

        elif name == "fx_rate":
            currency = args.get("currency", "달러")
            fx_map = {"달러": "FX@KRW", "유로": "FX@EUR", "엔": "FX@JPY"}
            code = fx_map.get(currency, "FX@KRW")
            rate = get_fx_rate(code)
            sign = "+" if rate["change_val"] > 0 else ""
            return (
                f"{currency}/원 환율: {rate['rate']:,.2f}원 "
                f"({sign}{rate['change_val']:.2f}, {sign}{rate['change_rate']:.2f}%) "
                f"| 고가 {rate['high']:,.2f} | 저가 {rate['low']:,.2f}"
            )

        return f"알 수 없는 도구: {name}"

    except Exception as e:
        return f"도구 실행 오류 ({name}): {e}"


# ─────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 kis-trader CLI 에이전트입니다.
한국투자증권 API를 통해 주식 조회, 매수/매도, 잔고 확인 등을 수행합니다.

## 규칙
1. 사용자가 주가를 물으면 stock_price 도구를 호출하세요.
2. 지수(코스피, 나스닥 등)를 물으면 market_index 도구를 호출하세요.
3. 뉴스, 왜 올랐어/떨어졌어 등을 물으면 stock_news 도구를 호출하세요.
4. 재무제표, PER, PBR 등을 물으면 financial_statement 도구를 호출하세요.
5. 잔고/보유종목을 물으면 check_balance 도구를 호출하세요.
6. 매수/매도 요청 시 반드시 종목, 수량, 가격을 확인한 후 실행하세요.
7. 거래량 순위를 물으면 volume_rank 도구를 호출하세요.
8. 환율을 물으면 fx_rate 도구를 호출하세요.

## 매수/매도 안전 규칙
- 매수/매도 주문 전에 반드시 사용자에게 종목, 수량, 가격을 확인받으세요.
- 확인 없이 절대 주문을 실행하지 마세요.
- 현재는 모의투자(paper) 모드입니다.

답변은 간결하고 읽기 쉽게 해주세요. 한국어로 답변하세요.
"""

# ─────────────────────────────────────────────
# 에이전트 루프
# ─────────────────────────────────────────────
def run_agent():
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[tool_declarations],
    )

    # 대화 히스토리
    history = []

    print("=" * 50)
    print("  kis-trader CLI Agent")
    print("  주식 조회, 매수/매도, 뉴스 등을 자연어로!")
    print("  종료: quit / exit / q")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q", "종료"):
            print("종료합니다.")
            break

        # 사용자 메시지 추가
        history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        try:
            # LLM 호출 + 도구 루프 (최대 5회)
            for _ in range(5):
                response = client.models.generate_content(
                    model=MODEL,
                    contents=history,
                    config=config,
                )

                candidate = response.candidates[0]

                # 함수 호출 확인
                func_calls = [p for p in candidate.content.parts if p.function_call]

                if not func_calls:
                    # 텍스트 응답 — 히스토리에 추가하고 출력
                    history.append(candidate.content)
                    text_parts = [p.text for p in candidate.content.parts if p.text]
                    text = "\n".join(text_parts)
                    if text:
                        print(f"\n{text}")
                    break

                # 함수 호출 실행
                # 먼저 assistant의 function_call을 히스토리에 추가
                history.append(candidate.content)

                func_response_parts = []
                for p in func_calls:
                    fc = p.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}
                    print(f"  [도구] {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")
                    result = execute_tool(tool_name, tool_args)
                    func_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": result},
                        )
                    )

                # 도구 결과를 히스토리에 추가
                history.append(types.Content(role="user", parts=func_response_parts))

        except Exception as e:
            print(f"\n오류: {e}")
            # 실패한 메시지는 히스토리에서 제거
            if history and history[-1].role == "user":
                history.pop()


if __name__ == "__main__":
    run_agent()

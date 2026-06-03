"""
ESG 등급 데이터 관리
한국ESG기준원(KCGS) 2024년 기준 주요 종목 ESG 등급
"""

# KCGS 2024 기준 주요 종목 ESG 등급 (종목코드: {등급 정보})
# 등급: S > A+ > A > B+ > B > C > D
GRADE_TO_SCORE = {"S": 95, "A+": 85, "A": 75, "B+": 65, "B": 55, "C": 35, "D": 15}

ESG_DATABASE = {
    "005930": {"name": "삼성전자", "total": "A+", "env": "A+", "social": "A", "gov": "A+", "year": 2024},
    "000660": {"name": "SK하이닉스", "total": "A+", "env": "A+", "social": "A+", "gov": "A", "year": 2024},
    "373220": {"name": "LG에너지솔루션", "total": "A", "env": "A+", "social": "A", "gov": "B+", "year": 2024},
    "207940": {"name": "삼성바이오로직스", "total": "A", "env": "A", "social": "A", "gov": "B+", "year": 2024},
    "005380": {"name": "현대차", "total": "A+", "env": "A+", "social": "A", "gov": "A", "year": 2024},
    "000270": {"name": "기아", "total": "A", "env": "A+", "social": "A", "gov": "B+", "year": 2024},
    "068270": {"name": "셀트리온", "total": "B+", "env": "B+", "social": "B+", "gov": "B+", "year": 2024},
    "005490": {"name": "포스코홀딩스", "total": "A+", "env": "A+", "social": "A+", "gov": "A", "year": 2024},
    "035720": {"name": "카카오", "total": "A", "env": "B+", "social": "A", "gov": "A", "year": 2024},
    "035420": {"name": "네이버", "total": "A+", "env": "A", "social": "A+", "gov": "A+", "year": 2024},
    "006400": {"name": "삼성SDI", "total": "A+", "env": "A+", "social": "A", "gov": "A", "year": 2024},
    "051910": {"name": "LG화학", "total": "A+", "env": "A+", "social": "A", "gov": "A", "year": 2024},
    "105560": {"name": "KB금융", "total": "A+", "env": "A", "social": "A+", "gov": "A+", "year": 2024},
    "055550": {"name": "신한지주", "total": "A+", "env": "A", "social": "A+", "gov": "A+", "year": 2024},
    "086790": {"name": "하나금융지주", "total": "A", "env": "A", "social": "A", "gov": "A", "year": 2024},
    "323410": {"name": "카카오뱅크", "total": "B+", "env": "B", "social": "A", "gov": "B+", "year": 2024},
    "003550": {"name": "LG", "total": "A+", "env": "A", "social": "A+", "gov": "A+", "year": 2024},
    "034730": {"name": "SK", "total": "A+", "env": "A+", "social": "A+", "gov": "A", "year": 2024},
    "028260": {"name": "삼성물산", "total": "A+", "env": "A+", "social": "A", "gov": "A+", "year": 2024},
    "096770": {"name": "SK이노베이션", "total": "A", "env": "A+", "social": "A", "gov": "B+", "year": 2024},
    "066570": {"name": "LG전자", "total": "A+", "env": "A+", "social": "A+", "gov": "A", "year": 2024},
    "003670": {"name": "포스코퓨처엠", "total": "A", "env": "A", "social": "A", "gov": "B+", "year": 2024},
    "012330": {"name": "현대모비스", "total": "A", "env": "A", "social": "A", "gov": "A", "year": 2024},
    "030200": {"name": "KT", "total": "A+", "env": "A", "social": "A+", "gov": "A+", "year": 2024},
    "017670": {"name": "SK텔레콤", "total": "A+", "env": "A", "social": "A+", "gov": "A+", "year": 2024},
    "001530": {"name": "DI동일", "total": "B", "env": "B", "social": "B", "gov": "B+", "year": 2024},
    "032640": {"name": "LG유플러스", "total": "A", "env": "A", "social": "A", "gov": "B+", "year": 2024},
    "009150": {"name": "삼성전기", "total": "A", "env": "A", "social": "A", "gov": "B+", "year": 2024},
    "010130": {"name": "고려아연", "total": "B+", "env": "A", "social": "B+", "gov": "B", "year": 2024},
    "011200": {"name": "HMM", "total": "B+", "env": "B+", "social": "B+", "gov": "B+", "year": 2024},
}


def get_esg(stock_code: str) -> dict:
    """종목코드로 ESG 등급 조회"""
    data = ESG_DATABASE.get(stock_code)
    if not data:
        return {
            "stock_code": stock_code, "stock_name": "",
            "total_grade": "", "env_grade": "", "social_grade": "", "gov_grade": "",
            "score": 0, "data_year": 0, "available": False,
        }
    return {
        "stock_code": stock_code,
        "stock_name": data["name"],
        "total_grade": data["total"],
        "env_grade": data["env"],
        "social_grade": data["social"],
        "gov_grade": data["gov"],
        "score": GRADE_TO_SCORE.get(data["total"], 0),
        "data_year": data["year"],
        "available": True,
    }


def check_esg_filter(stock_code: str, min_grade: str) -> dict:
    """ESG 등급 필터 체크. 통과 여부와 사유 반환"""
    if not min_grade:
        return {"passed": True, "reason": "ESG 필터 미적용"}

    grade_order = ["S", "A+", "A", "B+", "B", "C", "D"]
    esg = get_esg(stock_code)

    if not esg["available"]:
        return {"passed": False, "reason": f"ESG 등급 데이터 없음 ({stock_code})", "esg": esg}

    min_idx = grade_order.index(min_grade) if min_grade in grade_order else len(grade_order)
    stock_idx = grade_order.index(esg["total_grade"]) if esg["total_grade"] in grade_order else len(grade_order)

    if stock_idx <= min_idx:
        return {"passed": True, "reason": f"ESG {esg['total_grade']} (기준: {min_grade} 이상)", "esg": esg}
    else:
        return {"passed": False, "reason": f"ESG {esg['total_grade']} < 기준 {min_grade}", "esg": esg}

"""
종목-섹터 자동 맵핑 및 5대 핵심 섹터 자동 선정 모듈 (sector_classifier.py)
"""

import pandas as pd
from collector import get_stock_list

# 대표 핵심 섹터 분류 키워드 및 대표 종목 DB
SECTOR_MAPPER = {
    "AI 반도체 소부장 및 On-Device AI": [
        "반도체", "칩", "소부장", "HBM", "LPDDR", "마이크로디스플레이", "온디바이스", "메모리",
        "제주반도체", "피델릭스", "한양디지텍", "레이저쎌", "저스템", "라온텍", "코미코", "피엠티",
        "에스에이엠티", "KX하이텍", "성문전자", "미래산업", "앤씨앤", "코아시아씨엠", "케스피온",
        "한선엔지니어링", "제이케이시냅스", "알엔티엑스", "삼성전자", "SK하이닉스", "리노공업", "한미반도체"
    ],
    "제약·바이오 및 글로벌 헬스케어": [
        "제약", "바이오", "헬스케어", "의료기기", "임상", "진단", "백신", "생물보안법", "의료",
        "안국약품", "신풍", "에이프로젠", "차백신연구소", "엑세스바이오", "라메디텍", "엔젠바이오",
        "그린생명과학", "녹십자", "동화약품", "종근당", "제일약품", "보령", "경동제약", "환인제약",
        "대한뉴팜", "대웅제약", "안트로젠", "바이오플러스", "세운메디칼", "레이", "덴티스", "압타머"
    ],
    "기업 밸류업 및 저PBR 지주사": [
        "지주", "밸류업", "저PBR", "주주환원", "자사주", "금융", "리츠", "지배구조",
        "CR홀딩스", "유수홀딩스", "CJ", "종근당홀딩스", "오리온홀딩스", "제일파마홀딩스",
        "한진중공업홀딩스", "크라운해태홀딩스", "한세예스24홀딩스", "휴맥스홀딩스", "네오위즈홀딩스",
        "JW홀딩스", "진양홀딩스", "LX홀딩스", "GS", "코리안리", "롯데리츠", "KB스타리츠", "한국토지신탁",
        "LG", "SK네트웍스", "엠로", "쏘카", "소룩스", "큐로홀딩스", "모베이스"
    ],
    "로봇, 스마트팩토리 및 자동화 솔루션": [
        "로봇", "스마트팩토리", "자동화", "AMR", "협동로봇", "모터", "제어",
        "두산로보틱스", "아이로보틱스", "유디엠텍", "계양전기", "티플랙스", "티피씨글로벌",
        "레인보우로보틱스", "뉴로메카", "엔젤로보틱스", "에스피지", "티로보틱스"
    ],
    "K-푸드 및 필수소비재(음식료·유통)": [
        "푸드", "음식료", "소비재", "유통", "라면", "빙과", "건기식", "면세", "의류", "패션",
        "대한제당", "보락", "사조대림", "빙그레", "롯데칠성", "사조오양", "오뚜기",
        "우리손에프앤지", "동우팜투테이블", "선진", "크라운제과", "미트박스", "팜스빌",
        "현대홈쇼핑", "롯데하이마트", "신영와코루", "대현", "한세실업", "호전실업", "동인기연"
    ],
    "산업용 제지 및 친환경 포장재": [
        "제지", "포장", "박스", "펄프", "친환경",
        "무림SP", "한국수출포장", "아세아제지", "태림포장", "삼보판지", "한국제지", "신대양제지"
    ],
    "K-콘텐츠·게임 및 에듀테크": [
        "게임", "콘텐츠", "엔터", "에듀", "교육", "디지털교과서", "미디어",
        "위메이드플레이", "넥슨게임즈", "넷마블", "스튜디오드래곤", "카카오게임즈", "티쓰리",
        "바른손이앤에이", "팬스타엔터프라이즈", "고스트스튜디오", "와이지엔터테인먼트", "메가스터디",
        "아이스크림에듀", "아이비김영", "데이원컴퍼니", "아이스크림미디어", "오픈놀", "레뷰코퍼레이션", "노머스"
    ]
}


def classify_stock_to_sector(name: str, code: str) -> str:
    """종목명 및 코드 기반으로 가장 적합한 핵심 섹터 분류"""
    for sector_name, keywords in SECTOR_MAPPER.items():
        for kw in keywords:
            if kw in name:
                return sector_name
    return "기술 및 주도주 순환매"


def get_top5_sectors(screened_stocks: list) -> list:
    """
    포착 종목 리스트를 섹터별로 그룹화하고 상위 5대 핵심 섹터 추출
    
    Args:
        screened_stocks (list): [{'name': ..., 'code': ..., 'amount_100m': ...}]
        
    Returns:
        list: 5대 핵심 섹터 정보 리스트 (각 요소는 dict)
    """
    sector_groups = {}

    for stock in screened_stocks:
        name = stock["name"]
        code = stock["code"]
        sec = classify_stock_to_sector(name, code)

        if sec not in sector_groups:
            sector_groups[sec] = {
                "sector_name": sec,
                "stocks": [],
                "total_amount": 0.0,
                "count": 0
            }
        sector_groups[sec]["stocks"].append(name)
        sector_groups[sec]["total_amount"] += stock.get("amount_100m", 0.0)
        sector_groups[sec]["count"] += 1

    # 종목 수 및 거래대금 순 정렬
    sorted_sectors = sorted(
        sector_groups.values(),
        key=lambda x: (x["count"], x["total_amount"]),
        reverse=True
    )

    # 5개 미만인 경우 기본 5대 섹터 슬롯 채움
    default_sectors = list(SECTOR_MAPPER.keys())
    existing_names = [s["sector_name"] for s in sorted_sectors]

    for d_sec in default_sectors:
        if len(sorted_sectors) >= 5:
            break
        if d_sec not in existing_names:
            sorted_sectors.append({
                "sector_name": d_sec,
                "stocks": [],
                "total_amount": 0.0,
                "count": 0
            })

    top5 = sorted_sectors[:5]
    return top5

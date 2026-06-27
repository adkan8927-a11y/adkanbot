"""
stock_market_agent.py
증시 일반 일정 수집 에이전트
- 신규 공모 청약 일정
- IPO 신규 상장 일정
수집 소스: 38커뮤니케이션 (http://www.38.co.kr)
"""
import requests
import io
import re
import pandas as pd
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'http://www.38.co.kr/',
}


def _parse_date_range(date_str: str, year: int) -> list[str]:
    """
    '07/01 레메디' 또는 '2026.07.27~07.28' 형식 날짜 파싱
    Returns list of YYYY-MM-DD strings (첫 날짜만 반환)
    """
    dates = []

    # '2026.MM.DD~MM.DD' 형식
    m = re.search(r'(\d{4})[.\-](\d{2})[.\-](\d{2})', str(date_str))
    if m:
        dates.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
        return dates

    # 'MM/DD' 형식
    m = re.search(r'(\d{2})/(\d{2})', str(date_str))
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        # 연도 결정: 이미 지난 달이면 내년으로
        try:
            dt = datetime(year, month, day)
            if dt.date() < datetime.today().date() - timedelta(days=1):
                dt = datetime(year + 1, month, day)
            dates.append(dt.strftime('%Y-%m-%d'))
        except ValueError:
            pass
    return dates


def get_ipo_subscription_schedule() -> list[dict]:
    """38커뮤니케이션에서 공모 청약 일정 수집 (table index 23)"""
    schedules = []
    today = datetime.today()
    url = 'http://www.38.co.kr/html/fund/index.htm?o=s'  # 청약일정
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'euc-kr'
        tables = pd.read_html(io.StringIO(r.text), encoding='euc-kr')
    except Exception as e:
        print(f"  ❌ 청약일정 수집 실패: {e}")
        return []

    # 청약일정 테이블 찾기 ('종목명', '공모주일정' 컬럼 보유)
    target_table = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if '종목명' in cols and '공모주일정' in cols:
            target_table = t
            break

    if target_table is None:
        print("  ⚠️ 청약일정 테이블 미발견")
        return []

    for _, row in target_table.iterrows():
        name = str(row.get('종목명', '')).strip()
        date_range = str(row.get('공모주일정', '')).strip()
        if not name or name == 'nan' or not date_range or date_range == 'nan' or date_range == '-':
            continue

        # 시작 날짜 파싱 ('2026.07.27~07.28' 형식)
        dates = _parse_date_range(date_range, today.year)
        if not dates:
            continue

        start_date = dates[0]
        try:
            target_dt = datetime.strptime(start_date, '%Y-%m-%d')
            diff_days = (target_dt.date() - today.date()).days
            if diff_days < -1 or diff_days > 60:
                continue
        except ValueError:
            continue

        schedules.append({
            'date': start_date,
            'category': '공모청약',
            'event': f"[공모청약] {name}",
            'source': '38커뮤니케이션'
        })

    return schedules


def get_ipo_listing_schedule() -> list[dict]:
    """38커뮤니케이션에서 신규 상장 일정 수집"""
    schedules = []
    today = datetime.today()
    url = 'http://www.38.co.kr/html/fund/index.htm?o=l'  # 상장일정
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'euc-kr'
        tables = pd.read_html(io.StringIO(r.text), encoding='euc-kr')
    except Exception as e:
        print(f"  ❌ 신규상장 수집 실패: {e}")
        return []

    # 사이드 요약 테이블: '07/01 종목명' 형식의 1열 데이터
    # table[35~37]에 있는 신규상장 행을 찾음
    listing_items = []
    for t in tables:
        if t.shape[1] == 1:
            rows = t.iloc[:, 0].astype(str).tolist()
            # 'IPO 신규상장 일정' 헤더 행 이후 MM/DD 형식 행만 추출
            in_listing = False
            for val in rows:
                if 'IPO 신규상장' in val or '신규상장 일정' in val:
                    in_listing = True
                    continue
                if in_listing:
                    m = re.match(r'^(\d{2}/\d{2})\s+(.+)$', val.strip())
                    if m:
                        listing_items.append((m.group(1), m.group(2).strip()))
                    else:
                        # 다른 섹션 시작이면 종료
                        if val and not val.startswith('0') and len(val) > 5 and '/' not in val:
                            in_listing = False

    for date_str, name in listing_items:
        dates = _parse_date_range(date_str, today.year)
        if not dates:
            continue
        start_date = dates[0]
        try:
            target_dt = datetime.strptime(start_date, '%Y-%m-%d')
            diff_days = (target_dt.date() - today.date()).days
            if diff_days < -1 or diff_days > 60:
                continue
        except ValueError:
            continue

        schedules.append({
            'date': start_date,
            'category': '신규상장',
            'event': f"[신규상장] {name}",
            'source': '38커뮤니케이션'
        })

    return schedules


def get_options_expiry_schedule() -> list[dict]:
    """파생상품 옵션 만기일 정적 생성 (매월 두 번째 목요일)"""
    schedules = []
    today = datetime.today()

    for month_offset in range(3):  # 이번달 포함 3개월치
        year = today.year
        month = today.month + month_offset
        if month > 12:
            month -= 12
            year += 1

        # 해당 월의 두 번째 목요일 계산
        first_day = datetime(year, month, 1)
        # 0=Monday, 3=Thursday
        days_to_thursday = (3 - first_day.weekday()) % 7
        first_thursday = first_day + timedelta(days=days_to_thursday)
        second_thursday = first_thursday + timedelta(weeks=1)

        diff = (second_thursday.date() - today.date()).days
        if 0 <= diff <= 60:
            schedules.append({
                'date': second_thursday.strftime('%Y-%m-%d'),
                'category': '파생만기',
                'event': f"[파생만기] {year}년 {month}월 옵션 만기일",
                'source': '정적계산'
            })

    return schedules


def get_stock_market_schedules() -> list[dict]:
    """전체 증시 일반 일정 수집 통합 함수"""
    print("📥 [증시일정] 공모청약 일정 수집 중...")
    subs = get_ipo_subscription_schedule()
    print(f"  → {len(subs)}건 수집")

    print("📥 [증시일정] 신규상장 일정 수집 중...")
    listings = get_ipo_listing_schedule()
    print(f"  → {len(listings)}건 수집")

    print("📥 [증시일정] 옵션만기일 계산 중...")
    options = get_options_expiry_schedule()
    print(f"  → {len(options)}건 생성")

    return subs + listings + options


if __name__ == "__main__":
    result = get_stock_market_schedules()
    print(f"\n✅ 증시 일정 총 {len(result)}건 수집:")
    for s in result:
        print(f"  {s['date']} | {s['category']} | {s['event']}")

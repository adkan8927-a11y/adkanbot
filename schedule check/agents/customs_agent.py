import pandas as pd
from datetime import datetime, timedelta

def get_next_business_day(date_dt, holidays):
    """주말(토, 일) 및 공휴일인 경우 다음 영업일로 순연"""
    current = date_dt
    while True:
        # 주말 검사 (5: 토, 6: 일)
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        # 공휴일 검사
        date_str = current.strftime('%Y-%m-%d')
        if date_str in holidays:
            current += timedelta(days=1)
            continue
        break
    return current

def get_customs_schedules():
    print("🛃 [관세청 에이전트] 수출입 동향 발표(예정)일 산출 중...")
    
    # 2026년 국내 주요 법정 공휴일 정의 (설/추석 포함)
    holidays_2026 = {
        "2026-01-01",  # 신정
        "2026-02-16", "2026-02-17", "2026-02-18",  # 설날 연휴
        "2026-03-01",  # 삼일절
        "2026-03-02",  # 삼일절 대체공휴일
        "2026-05-05",  # 어린이날
        "2026-05-24",  # 석가탄신일
        "2026-05-25",  # 석가탄신일 대체공휴일
        "2026-06-06",  # 현충일
        "2026-08-15",  # 광복절
        "2026-08-17",  # 광복절 대체공휴일
        "2026-09-24", "2026-09-25", "2026-09-26",  # 추석 연휴
        "2026-10-03",  # 개천절
        "2026-10-05",  # 개천절 대체공휴일
        "2026-10-09",  # 한글날
        "2026-12-25"   # 성탄절
    }
    
    today_dt = datetime.today()
    schedules = []
    
    # 오늘 기준 전후 1개월(총 2개월) 기간 내의 발표일 생성
    start_dt = today_dt - timedelta(days=35)
    end_dt = today_dt + timedelta(days=35)
    
    # 해당 기간의 연도와 월 목록 추출
    months_to_check = []
    curr = start_dt
    while curr <= end_dt:
        ym = (curr.year, curr.month)
        if ym not in months_to_check:
            months_to_check.append(ym)
        curr += timedelta(days=15)
        
    for year, month in months_to_check:
        # 매월 1일(전월 전체), 11일(당월 1~10일), 21일(당월 1~20일) 기준일
        for day, label in [(1, "월간"), (11, "10일 단위"), (21, "20일 단위")]:
            try:
                base_date = datetime(year, month, day)
                # 수집 기간 내에 들어오는지 체크
                if start_dt <= base_date <= end_dt:
                    # 실제 발표일(영업일 기준 순연)
                    release_dt = get_next_business_day(base_date, holidays_2026)
                    release_date_str = release_dt.strftime('%Y-%m-%d')
                    
                    # 오늘 날짜 이후의 예정일만 등록
                    if release_dt.date() >= today_dt.date():
                        schedules.append({
                            "date": release_date_str,
                            "category": "경제 일반",
                            "event": f"[수출입] 관세청 {label} 수출입 동향 발표(예정)일",
                            "source": "관세청"
                        })
            except ValueError:
                continue
                
    # 날짜 정렬 및 중복 제거
    schedules = sorted(schedules, key=lambda x: x['date'])
    print(f"  🎉 관세청 발표 예정 일정 {len(schedules)}건 산출 완료!")
    return schedules

if __name__ == "__main__":
    res = get_customs_schedules()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

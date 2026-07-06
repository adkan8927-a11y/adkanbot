import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import os

def get_historical_cb_overhang():
    print("⏳ [CB 백필링 에이전트] 1년 전 DART CB 공시 스캔 중...")
    
    # 1. 타겟 기간 설정 (1년 전의 '오늘'부터 30일간)
    today = datetime.today()
    target_start = today - relativedelta(years=1)
    target_end = target_start + relativedelta(days=30)
    
    bgn_de = target_start.strftime("%Y%m%d")
    end_de = target_end.strftime("%Y%m%d")
    
    # dart_agent.py와 동일한 DART API KEY 사용
    DART_API_KEY = os.environ.get("DART_API_KEY", "63cfc7d9c10a4c87a2e735d31f8ff4c4351207de")
    
    try:
        import OpenDartReader
        dart = OpenDartReader(DART_API_KEY)
        
        # 'Y'(유가증권), 'K'(코스닥) 상장사의 공시만 필터링하기 위해 전체 조회 후 필터링
        df = dart.list(start=bgn_de, end=end_de)
        schedules = []
        
        if df is not None and not df.empty:
            df = df[df['corp_cls'].isin(['Y', 'K'])]
            cb_reports = df[df['report_nm'].str.contains('전환사채권발행결정|신주인수권부사채권발행결정', na=False)]
            
            for _, row in cb_reports.iterrows():
                report_nm = str(row['report_nm'])
                company = str(row['corp_name'])
                rcept_dt = str(row['rcept_dt']) # 예: 20250715
                
                try:
                    # 1년 뒤 날짜(행사가능일) 자동 계산
                    issue_date = datetime.strptime(rcept_dt, '%Y%m%d')
                    release_date = issue_date + relativedelta(years=1)
                    release_date_str = release_date.strftime('%Y-%m-%d')
                    
                    event_text = f"[잠재매도] {company} CB/BW 전환청구 가능 (1년 전 발행)"
                    
                    schedules.append({
                        "date": release_date_str,
                        "category": "오버행(잠재매도)",
                        "event": event_text,
                        "source": "DART(과거검색)"
                    })
                except Exception as parse_e:
                    print(f"  ⚠️ CB 공시 날짜 파싱 오류: {parse_e}")
                    
        print(f"  🎉 CB 오버행 일정 {len(schedules)}건 수집 완료!")
        return schedules
        
    except Exception as e:
        print(f"  ❌ 과거 데이터 백필링 중 에러 발생: {e}")
        return []

if __name__ == "__main__":
    res = get_historical_cb_overhang()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

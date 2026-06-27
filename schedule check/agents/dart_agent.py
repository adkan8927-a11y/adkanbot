import OpenDartReader
from datetime import datetime

def get_dart_schedules():
    api_key = '63cfc7d9c10a4c87a2e735d31f8ff4c4351207de'
    try:
        dart = OpenDartReader(api_key)
        # 오늘 날짜
        today_dt = datetime.today()
        # 주말 대응 (토요일이면 어제 금요일, 일요일이면 그저께 금요일)
        from datetime import timedelta
        if today_dt.weekday() == 5: # 토요일
            query_date = (today_dt - timedelta(days=1)).strftime('%Y%m%d')
        elif today_dt.weekday() == 6: # 일요일
            query_date = (today_dt - timedelta(days=2)).strftime('%Y%m%d')
        else:
            query_date = today_dt.strftime('%Y%m%d')
            
        df = dart.list(start=query_date, end=query_date)
        
        schedules = []
        if df is not None and not df.empty:
            target_keywords = '실적|단일판매|증자|소각|합병|분할'
            important_reports = df[df['report_nm'].str.contains(target_keywords, regex=True, na=False)]
            for _, row in important_reports.iterrows():
                rcept_dt_formatted = datetime.strptime(row['rcept_dt'], '%Y%m%d').strftime('%Y-%m-%d')
                schedules.append({
                    "date": rcept_dt_formatted,
                    "category": "경제 일반",
                    "event": f"[{row['corp_name']}] {row['report_nm']}",
                    "source": "DART"
                })
        return schedules
    except Exception as e:
        print(f"❌ DART 수집 에러: {e}")
        return []

if __name__ == "__main__":
    res = get_dart_schedules()
    print("DART 수집 결과:", res)

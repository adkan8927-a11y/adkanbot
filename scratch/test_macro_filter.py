import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv("schedule check/master_schedule_db.csv")
today_dt = datetime.strptime("2026-08-09", "%Y-%m-%d")

major_macro = None
major_conf = None
major_earnings = None

for _, row in df.iterrows():
    event_date = str(row['date']).strip()
    try:
        target_dt = datetime.strptime(event_date, "%Y-%m-%d")
        diff_days = (target_dt.date() - today_dt.date()).days
    except:
        continue

    if diff_days < 0:
        continue

    source = str(row.get('source', '')).strip().upper()
    category = str(row.get('category', '')).strip()
    event_text = str(row['event']).strip()

    if diff_days <= 60:
        # FRED API 이미 발표된 결과값 데이터 제외
        is_already_published_fred = ('FRED' in source) or ('발표일:' in event_text)
        
        is_macro = (
            not is_already_published_fred and (
                category in ('정부정책', '거시 지표', '거시 일정', '국제 - 미국', '매크로') or 
                any(kw in event_text.upper() for kw in ('FOMC', 'CPI', 'PPI', '금리', 'FED', '연준', '물가'))
            )
        )
        if is_macro and not major_macro:
            major_macro = {"date": event_date, "text": event_text, "cat": "매크로"}
        elif (category == '글로벌학회' or category == '학회') and not major_conf:
            major_conf = {"date": event_date, "text": event_text, "cat": "학회"}
        elif category == '실적발표' and not major_earnings:
            major_earnings = {"date": event_date, "text": event_text, "cat": "실적"}

print("Major Macro Selected:", major_macro)
print("Major Conf Selected:", major_conf)
print("Major Earnings Selected:", major_earnings)

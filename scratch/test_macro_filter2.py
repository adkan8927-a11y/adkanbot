import pandas as pd
from datetime import datetime

df = pd.read_csv("schedule check/master_schedule_db.csv")
today_dt = datetime.strptime("2026-08-09", "%Y-%m-%d")

major_macro = None

# 1. First pass: look specifically for CPI, FOMC, PPI, 금리, Fed macro indicators scheduled on or after today
for _, row in df.iterrows():
    event_date = str(row['date']).strip()
    try:
        target_dt = datetime.strptime(event_date, "%Y-%m-%d")
        diff_days = (target_dt.date() - today_dt.date()).days
    except:
        continue

    if diff_days < 0 or diff_days > 60:
        continue

    source = str(row.get('source', '')).strip().upper()
    category = str(row.get('category', '')).strip()
    event_text = str(row['event']).strip()

    is_already_published_fred = ('FRED' in source) or ('발표일:' in event_text)
    if is_already_published_fred:
        continue

    is_high_impact_macro = (
        category == '거시 일정' or 
        any(kw in event_text.upper() for kw in ('FOMC', 'CPI', 'PPI', '금리', 'FED', '연준', '소비자물가', '인플레이션'))
    )
    if is_high_impact_macro:
        major_macro = {"date": event_date, "text": event_text, "cat": "매크로"}
        break

print("Prioritized Macro Selected:", major_macro)

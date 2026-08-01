import os
import sys
import pandas as pd
from datetime import datetime

print("🚀 8월 의무보유등록(보호예수) 해제 PDF 46건 파싱 및 DB 업데이트 시작...")

sys.path.append("schedule check/agents")
from pdf_lockup_agent import get_pdf_lockup_schedules

schedules = get_pdf_lockup_schedules()
print(f"✅ {len(schedules)}건의 8월 보호예수 해제 일정 추출 완료!")

csv_path = "schedule check/master_schedule_db.csv"
old_df = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame()
new_df = pd.DataFrame(schedules)

combined_df = pd.concat([old_df, new_df], ignore_index=True)
combined_df["date"] = combined_df["date"].astype(str).str.strip()
combined_df["event"] = combined_df["event"].astype(str).str.strip()
combined_df = combined_df.drop_duplicates(subset=["date", "event"], keep="last")
combined_df = combined_df.sort_values(by="date")

combined_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"💾 마스터 DB 업데이트 완료: 총 {len(combined_df)}건 저장 완료!")

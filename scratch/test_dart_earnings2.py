import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../schedule check/agents')))
from dart_agent import get_dart_schedules, OpenDartReader, clean_html, extract_dates_from_report

def test_earnings():
    dart = OpenDartReader('63cfc7d9c10a4c87a2e735d31f8ff4c4351207de')
    end_date = datetime.today()
    start_date = end_date - timedelta(days=90)
    print(f"Querying DART from {start_date.strftime('%Y%m%d')} to {end_date.strftime('%Y%m%d')}")
    df = dart.list(start=start_date.strftime('%Y%m%d'), end=end_date.strftime('%Y%m%d'))
    if df is not None and not df.empty:
        earnings_reports = df[df['report_nm'].str.contains('실적발표예고|실적발표 예정', regex=True, na=False)]
        for _, row in earnings_reports.iterrows():
            print(f"Found: {row['corp_name']} - {row['report_nm']} ({row['rcept_no']})")
            doc_raw = dart.document(row['rcept_no'])
            if doc_raw:
                doc_text = clean_html(doc_raw)
                extracted = extract_dates_from_report(doc_text, row['report_nm'])
                print("  Extracted dates:", extracted)

if __name__ == "__main__":
    test_earnings()

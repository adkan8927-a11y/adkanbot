import requests
import os

DART_API_KEY = "63cfc7d9c10a4c87a2e735d31f8ff4c4351207de"
url = "https://opendart.fss.or.kr/api/list.json"
bgn_de = "20250615"
end_de = "20250715"

schedules = []

try:
    for market in ['Y', 'K']:
        params = {
            'crtfc_key': DART_API_KEY,
            'bgn_de': bgn_de,
            'end_de': end_de,
            'page_count': '100',
            'corp_cls': market
        }
        res = requests.get(url, params=params)
        data = res.json()
        if data.get('status') == '000':
            for item in data.get('list', []):
                report_nm = item.get('report_nm', '')
                if '전환사채권발행결정' in report_nm or '신주인수권부사채권발행결정' in report_nm:
                    corp_name = item.get('corp_name')
                    rcept_dt = item.get('rcept_dt')
                    schedules.append(f"{rcept_dt} | {corp_name} | {report_nm}")
except Exception as e:
    print("Error:", e)

if schedules:
    print(f"총 {len(schedules)}건의 공시 발견:")
    for s in schedules:
        print("  -", s)
else:
    print("해당 기간에 검색된 공시가 없습니다.")

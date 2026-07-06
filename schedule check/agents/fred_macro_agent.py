import requests
from datetime import datetime, timedelta

API_KEY = "e7d85567b65d7dec6884a801bdf9af4c"

class FredMacroAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        
        # 봇에서 추적할 주요 거시 지표 Series ID 매핑
        self.key_series = {
            "DFF": "🇺🇸 미국 실효연방기금금리 (기준금리)",
            "DGS10": "🇺🇸 미국 10년물 국채 금리",
            "CPIAUCSL": "🛒 미국 소비자물가지수(CPI)",
            "UNRATE": "💼 미국 실업률"
        }

    def get_latest_indicators(self) -> dict:
        results = {}
        url = f"{self.base_url}/series/observations"
        
        for series_id, desc in self.key_series.items():
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "observations" in data and data["observations"]:
                        obs = data["observations"][0]
                        results[desc] = {
                            "date": obs["date"],
                            "value": obs["value"]
                        }
            except Exception as e:
                pass
                
        return results

    def get_upcoming_releases(self, days=7) -> list:
        url = f"{self.base_url}/releases/dates"
        today = datetime.now()
        end_date = today + timedelta(days=days)
        
        params = {
            "api_key": self.api_key,
            "file_type": "json",
            "realtime_start": today.strftime("%Y-%m-%d"),
            "realtime_end": end_date.strftime("%Y-%m-%d"),
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                releases = []
                if "release_dates" in data:
                    for release in data["release_dates"][:10]: 
                        releases.append({
                            "date": release["date"],
                            "name": release.get("release_name", "이름 없음")
                        })
                return releases
        except Exception:
            pass
        return []

def get_fred_macro_schedules():
    print("📈 [FRED 매크로 에이전트] 미국 연준 공식 경제 지표 수집 중...")
    
    agent = FredMacroAgent(api_key=API_KEY)
    schedules = []
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # 1. 최신 지표 고정 노출 (오늘 날짜로 강제 주입하여 항상 상단에 보이게 함)
    indicators = agent.get_latest_indicators()
    for desc, data in indicators.items():
        event_text = f"[매크로] {desc} : {data['value']}% (발표일: {data['date']})"
        schedules.append({
            "date": today_str,
            "category": "거시 지표",
            "event": event_text,
            "source": "FRED API"
        })
        
    # 2. 이번 주 주요 지표 발표 일정
    upcoming = agent.get_upcoming_releases(days=7)
    for item in upcoming:
        event_text = f"[발표예정] {item['name']}"
        schedules.append({
            "date": item['date'],
            "category": "거시 일정",
            "event": event_text,
            "source": "FRED API"
        })
        
    print(f"  🎉 FRED 거시 지표 및 일정 {len(schedules)}건 수집 완료!")
    return schedules

if __name__ == "__main__":
    res = get_fred_macro_schedules()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

import requests
from datetime import datetime, timedelta

def get_macro_schedules():
    fmp_api_key = "y3PCnQhXrf55v9fcS3FZy21H7uEYrEXA"
    today = datetime.today().strftime('%Y-%m-%d')
    end_date = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={today}&to={end_date}&apikey={fmp_api_key}"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            schedules = []
            for item in data:
                if item.get('country') == 'US' and item.get('impact') == 'High':
                    schedules.append({
                        "date": item.get('date')[:10],
                        "category": "국제 - 미국",
                        "event": f"{item.get('event')} (이전: {item.get('previous')}, 예상: {item.get('estimate')})",
                        "source": "FMP API"
                    })
            return schedules
        else:
            print(f"❌ FMP API 호출 실패 (코드: {response.status_code})")
            return []
    except Exception as e:
        print(f"❌ FMP API 수집 에러: {e}")
        return []

if __name__ == "__main__":
    res = get_macro_schedules()
    print("Macro 수집 결과:", res)

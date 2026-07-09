import yfinance as yf
from datetime import datetime, date
import os
import sys

def get_earnings_schedule():
    print("📈 [빅테크 실적 에이전트] 주요 기업 실적발표 일정 수집 중...")
    
    TICKERS = {
        # M7 Big Tech
        'AAPL': '애플',
        'MSFT': '마이크로소프트',
        'NVDA': '엔비디아',
        'GOOGL': '알파벳',
        'AMZN': '아마존',
        'META': '메타',
        'TSLA': '테슬라',
        
        # K-Big Tech
        '005930.KS': '삼성전자',
        '000660.KS': 'SK하이닉스',
        '035420.KS': '네이버',
        '035720.KS': '카카오'
    }
    
    results = []
    today = date.today()
    
    for symbol, name in TICKERS.items():
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            
            if cal and 'Earnings Date' in cal and cal['Earnings Date']:
                earnings_dates = cal['Earnings Date']
                # 보통 배열로 반환됨
                for e_date in earnings_dates:
                    if isinstance(e_date, date):
                        # 오늘 이후 일정만 (최대 90일 내)
                        diff = (e_date - today).days
                        if 0 <= diff <= 90:
                            results.append({
                                'date': e_date.strftime('%Y-%m-%d'),
                                'category': '실적발표',
                                'event': f"{name} 실적발표",
                                'source': 'YFINANCE'
                            })
                            print(f"  ✅ {name} 실적발표 확인: {e_date}")
        except Exception as e:
            print(f"  ⚠️ {name}({symbol}) 실적 수집 실패: {e}")
            
    return results

if __name__ == "__main__":
    schedules = get_earnings_schedule()
    for s in schedules:
        print(s)

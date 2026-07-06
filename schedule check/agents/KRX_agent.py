import requests
import io
import pandas as pd
from datetime import datetime
import os

def get_krx_market_alerts():
    print("🚨 KRX KIND 시장조치 및 추가상장 공시 수집 중...")
    
    url = "https://kind.krx.co.kr/disclosure/todaydisclosure.do"
    today = datetime.today().strftime('%Y-%m-%d')
    
    payload = {
        'method': 'searchTodayDisclosureSub',
        'selDate': today
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    schedules = []
    
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        
        # StringIO를 사용하여 pandas 경고 방지 및 HTML 표 파싱
        tables = pd.read_html(io.StringIO(response.text))
        
        if not tables:
            print("  ⚠️ 오늘은 등록된 공시가 없습니다.")
            return schedules
            
        df = tables[0] # 첫 번째 표가 당일 공시 목록
        
        # 컬럼 존재 확인 및 이름 표준화
        if '공시제목' not in df.columns or '회사명' not in df.columns:
            print("  ⚠️ 필요한 컬럼(공시제목/회사명)을 찾지 못했습니다.")
            return schedules
            
        # 수집된 공시 중 주가와 매매 방식에 직결되는 키워드만 필터링
        target_keywords = '단기과열|투자경고|투자주의|거래정지|추가상장|불성실|상장폐지'
        
        alerts_df = df[df['공시제목'].str.contains(target_keywords, regex=True, na=False)].copy()
        
        if not alerts_df.empty:
            for _, row in alerts_df.iterrows():
                corp_name = str(row['회사명']).strip()
                title = str(row['공시제목']).strip()
                
                # 중복이나 정렬 및 대시보드 뷰어 형식에 깔끔하게 맞추기
                schedules.append({
                    "date": today,
                    "category": "KRX 시장조치",
                    "event": f"[{corp_name}] {title}",
                    "source": "KRX"
                })
            print(f"  → 주요 시장조치 / 추가상장 {len(schedules)}건 포착 완료")
        else:
            print("  → 오늘은 시장에 영향을 줄 만한 특이 공시(과열/추가상장 등)가 없습니다.")
            
    except Exception as e:
        print(f"❌ KIND 공시 수집 중 에러 발생: {e}")
        
    return schedules

if __name__ == "__main__":
    res = get_krx_market_alerts()
    print("수집 결과:", res)
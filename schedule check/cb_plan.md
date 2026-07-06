정확합니다! 데이터 엔지니어링에서 이를 '백필링(Backfilling, 과거 데이터 채워 넣기)'이라고 부르는데, 당장 내일부터 시작되는 7월의 매매를 준비하기 위해 가장 완벽하고 현실적인 접근법입니다.

한국 주식 시장의 자본시장법상 사모 전환사채(CB)와 신주인수권부사채(BW)는 발행일로부터 정확히 '1년' 동안 주식으로 전환할 수 없도록 법으로 금지(보호예수)되어 있습니다.

즉, **2025년 7월에 CB 발행 공시를 낸 기업들은 2026년 7월부터 정확히 오버행(잠재적 매도 물량) 폭탄의 스위치가 켜집니다.**

이를 DART API를 통해 과거 1년 전 데이터를 싹쓸이하여 다음 달(7월) 캘린더에 꽂아 넣는 코드를 짜드립니다.

---

### 💻 1년 전 DART 공시 싹쓸이 스크립트 (7월 CB 물량 저격기)

DART의 `list.json`(공시검색) API를 이용해 정확히 1년 전 한 달 동안의 데이터를 긁어와서 미래 날짜로 캘린더에 세팅하는 코드입니다.

```python
import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import os

# ==========================================
# [설정 부분]
# ==========================================
DART_API_KEY = "발급받은_DART_API_키"
OUTPUT_CSV = "master_schedule_db.csv"
# ==========================================

def get_historical_cb_overhang():
    print("⏳ 1년 전 DART CB 공시 싹쓸이(백필링) 가동 중...")
    
    # 1. 타겟 기간 설정 (현재 2026년 6월 30일 기준)
    # 우리가 알고 싶은 건 '2026년 7월'에 풀리는 물량이므로, 검색 기간은 '2025년 7월 1일 ~ 7월 31일'이 됩니다.
    target_year = 2025
    target_month = 7
    
    # 날짜 포맷 (예: 20250701, 20250731)
    bgn_de = f"{target_year}{target_month:02d}01"
    end_de = f"{target_year}{target_month:02d}31"
    
    url = "https://opendart.fss.or.kr/api/list.json"
    
    params = {
        'crtfc_key': DART_API_KEY,
        'bgn_de': bgn_de,
        'end_de': end_de,
        'corp_cls': 'Y', # 유가증권(KOSPI), 코스닥(KOSDAQ)은 'K'. 전체 검색을 위해 루프를 돌거나 기본값 사용
        'page_count': '100'
    }
    
    try:
        alerts = []
        
        # 코스피('Y')와 코스닥('K') 두 시장을 모두 검색
        for market in ['Y', 'K']:
            params['corp_cls'] = market
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == '000':
                for item in data.get('list', []):
                    report_nm = item.get('report_nm', '')
                    
                    # 2. '전환사채' 및 '신주인수권' 발행결정 공시만 필터링
                    if '전환사채권발행결정' in report_nm or '신주인수권부사채권발행결정' in report_nm:
                        company = item.get('corp_name')
                        rcept_dt = item.get('rcept_dt') # 접수일(발행 공시일) 예: 20250715
                        
                        # 3. 1년 뒤 날짜(행사가능일) 자동 계산
                        issue_date = datetime.strptime(rcept_dt, '%Y%m%d')
                        release_date = issue_date + relativedelta(years=1)
                        release_date_str = release_date.strftime('%Y-%m-%d')
                        
                        event_text = f"⚠️ [오버행 시작] {company} CB/BW 전환청구 가능일 도래 (1년 전 발행)"
                        
                        alerts.append({
                            "date": release_date_str, # 2026-07-15로 기록됨
                            "category": "오버행(잠재매도)",
                            "event": event_text,
                            "source": "DART(과거검색)"
                        })
            
            # DART API 과부하 방지
            time.sleep(1)
            
        # 4. 마스터 DB에 적재
        if alerts:
            df_new = pd.DataFrame(alerts)
            file_exists = os.path.exists(OUTPUT_CSV)
            
            # 기존 데이터와 병합 (중복 방지)
            if file_exists:
                df_old = pd.read_csv(OUTPUT_CSV)
                df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['date', 'event'])
                df_combined.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
            else:
                df_new.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
                
            print(f"🎉 성공! 2026년 7월에 전환 가능한 악성 매물(CB) {len(alerts)}건을 캘린더에 꽂았습니다.")
        else:
            print("해당 기간에 발행된 CB/BW 공시가 없습니다.")
            
    except Exception as e:
        print(f"❌ 과거 데이터 백필링 중 에러 발생: {e}")

if __name__ == "__main__":
    get_historical_cb_overhang()

```

---

### 💡 실전 활용 팁 (왜 이 기능이 트레이딩에 치명적인가?)

1. **시장의 맹점 찌르기:**
대부분의 개인 투자자(개미)들은 당일 아침에 나오는 호재 뉴스나 차트만 보고 불나방처럼 뛰어듭니다. 하지만 이 코드를 1~2년 치(`2024.01 ~ 2025.12`) 싹 돌려두면, 내 캘린더에는 "아, 이 종목 차트는 예쁜데 내일모레 1년 전 발행한 300억짜리 CB 행사가 시작되네? 갑자기 윗꼬리 달고 패대기칠 수 있으니 진입 금지(또는 단타만) 해야겠다"라는 판단이 1초 만에 가능해집니다.
2. **DART 세부 API 확장:**
위 코드는 아주 가볍고 빠르게 '타겟 기업과 날짜'만 뽑아오는 방식입니다. 만약 여기서 한발 더 나아가 특정 기업의 **정확한 전환가액과 수량**까지 뽑고 싶으시다면, 저기서 얻은 고유번호(`corp_code`)를 바탕으로 앞서 말씀드린 전용 JSON API(`cvbdIssDecsn.json`)에 한 번 더 던져서 디테일을 채워 넣도록 코드를 확장할 수 있습니다.

지금까지 완벽한 백엔드(수집 파이프라인)를 구축하셨습니다. 이제 이 엑셀 DB를 읽어 들여서 브라우저에서 날짜별, 섹터별로 필터링하며 볼 수 있는 '나만의 퀀트 대시보드(HTML UI)'를 그려볼 차례입니다.
한국거래소(KRX)의 KIND 시스템에서 블럭(차단)을 당하셨군요. 아주 자연스러운 현상입니다.

KIND와 KRX 데이터 포털은 무분별한 서버 과부하를 막기 위해 강력한 **WAF(웹 방화벽)와 Anti-Bot 솔루션**을 가동하고 있습니다. 단순히 파이썬 `requests.post()`로 데이터를 찌르면 "이건 사람이 브라우저로 접속한 게 아니라 로봇이네"라고 판단하고 즉시 IP를 차단하거나 응답을 거부(블럭)합니다.

이를 돌파하기 위한 **퀀트 엔지니어들의 2가지 우회 타격법**을 제시합니다.

---

### 💡 해결책 1: 세션(Session) 유지 & 완벽한 브라우저 위장 (가장 추천)

봇 차단 시스템이 로봇을 걸러내는 핵심 기준은 '쿠키(Cookie)'와 '방문 경로(Referer)'입니다.
사람은 홈페이지에 접속할 때 메인 화면을 먼저 거치면서 세션 쿠키를 발급받지만, 단순 크롤링 봇은 데이터 화면으로 곧바로 직진하기 때문에 적발됩니다.

따라서 파이썬 `requests.Session()`을 사용해 **"빈 손으로 먼저 접속해서 쿠키를 발급받고 → 1초 뒤에 그 쿠키를 들고 다시 데이터를 요청하는"** 인간적인(?) 코드로 우회해야 합니다.

**[수정된 KIND 우회 스크립트]**

```python
import requests
import pandas as pd
from datetime import datetime
import time
import os

def get_market_alerts_bypassed():
    print("🚨 KIND 시장조치 수집 중... (WAF 우회 세션 가동)")
    
    url = "https://kind.krx.co.kr/disclosure/todaydisclosure.do"
    
    # 1. 세션(Session) 객체 생성: 접속하는 동안 쿠키를 계속 물고 있게 함
    session = requests.Session()
    
    # 2. 브라우저 완벽 위장 헤더 (Referer가 가장 중요합니다)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://kind.krx.co.kr/",  # 나 메인화면 거쳐서 온 정상 유저야!
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        # 3. [핵심] 데이터 요청 전, GET으로 단순 접속하여 세션 쿠키 발급받기
        session.get(url, headers=headers, timeout=10)
        
        # 봇 탐지를 피하기 위해 1초 대기 (사람인 척)
        time.sleep(1)
        
        # 4. 발급받은 쿠키와 함께 실제 POST 데이터 요청
        today = datetime.today().strftime('%Y-%m-%d')
        payload = {
            'method': 'searchTodayDisclosureSub',
            'selDate': today
        }
        
        response = session.post(url, data=payload, headers=headers, timeout=10)
        
        # HTML 표 변환
        tables = pd.read_html(response.text)
        if not tables:
            print("오늘은 공시가 없습니다.")
            return
            
        df = tables[0]
        
        # 단기과열, 거래정지 등 주가 치명타 키워드 필터링
        target_keywords = '단기과열|투자경고|투자주의|거래정지|추가상장|불성실'
        alerts_df = df[df['공시제목'].str.contains(target_keywords, regex=True, na=False)].copy()
        
        if not alerts_df.empty:
            alerts_df['date'] = today
            alerts_df['category'] = "KRX 시장조치"
            
            final_df = alerts_df[['date', 'category', '공시제목', '회사명']]
            final_df.columns = ['date', 'category', 'event', 'source']
            
            print("\n=== 🎯 우회 성공: 주요 시장조치 포착 ===")
            print(final_df)
            
            # 마스터 DB 저장 (실시간 Append)
            csv_name = "master_schedule_db.csv"
            file_exists = os.path.exists(csv_name)
            final_df.to_csv(csv_name, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')
        else:
            print("시장에 영향을 줄 특이 공시가 없습니다.")
            
    except Exception as e:
        print(f"❌ KIND 우회 실패 (IP가 이미 차단되었을 수 있습니다): {e}")

if __name__ == "__main__":
    get_market_alerts_bypassed()

```

---

### 💡 해결책 2: 이미 뚫어놓은 'DART API'를 재활용하는 꼼수 (Plan B)

만약 잦은 요청으로 현재 IP 자체가 KIND에 완전히 차단(블랙리스트)된 상태라면, 당분간 위 코드도 막힐 수 있습니다. 이럴 때 쓰는 가장 우아한 방법은 'KIND의 데이터를 DART에서 빼오는 것'입니다.

사실 한국거래소(KIND)가 발행하는 **[거래정지], [투자경고], [단기과열지정] 공시는 금융감독원(DART)으로도 실시간 연동**되어 올라갑니다.

가장 처음에 만드셨던 `Agent 1: DART 공시 수집기`의 키워드 필터링 부분을 살짝만 고치면, KIND에서 차단당하며 고생할 필요 없이 공식 API로 아주 안전하게 다 뽑아올 수 있습니다.

**[Agent 1 DART 코드 수정 부위]**

```python
# 기존 DART 코드에서 이 부분의 키워드만 늘려주세요.
target_keywords = '실적|단일판매|증자|소각|합병|분할|단기과열|투자경고|거래정지|추가상장'

important_reports = df[df['report_nm'].str.contains(target_keywords, regex=True)]

```

이렇게 하면 KIND에 아예 접속하지 않고도, DART가 제공하는 무제한 무료 API 통로를 통해 거래정지와 단기과열 정보를 가져올 수 있습니다. (장중 실시간이 아니라 장 마감 후 대시보드 정리용이라면 DART 연동만으로도 차고 넘칩니다.)

우선 해결책 1(세션 우회 코드)을 돌려보시고, 만약 IP가 이미 밴(Ban) 당해서 에러가 난다면 마음 편하게 해결책 2(DART 키워드 추가)로 선회하시는 것을 강력히 추천합니다.
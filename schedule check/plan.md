plan1

크롤링(웹 스크래핑)과 API를 활용해 데이터를 직접 당겨오는 4가지 방법의 구체적인 파이썬 구현 코드를 정리해 드립니다.

웹 사이트를 무작정 긁어오는 것은 사이트 구조가 바뀌거나 보안(Cloudflare 등)에 막히면 코드가 고장 나기 쉽습니다. 따라서 **가장 고장이 안 나고 유지보수가 편한 '공식 API'와 'RSS'를 최우선으로 활용하는 방향**으로 코드를 설계했습니다.

---

### 1. 국내 기업 공시 및 실적 (DART API)

금융감독원 DART(전자공시시스템)는 완벽하게 구조화된 무료 API를 제공합니다. 기업의 유상증자, 무상증자, 실적발표, 단일판매 공급계약 등 주가에 직결되는 확정 일정을 100% 정확하게 가져올 수 있습니다.

* **준비물:** DART 오픈 API 사이트(opendart.fss.or.kr)에서 무료 API 키 발급
* **설치:** `pip install OpenDartReader pandas`

```python
import OpenDartReader
import pandas as pd
from datetime import datetime

# 1. DART API 키 입력
api_key = '63cfc7d9c10a4c87a2e735d31f8ff4c4351207de'
dart = OpenDartReader(api_key)

# 2. 오늘 날짜 기준으로 검색 (예: 2026-06-16)
today = datetime.today().strftime('%Y%m%d')

print(f"[{today}] 주요 공시 수집 시작...")

# 3. 오늘 하루 동안 올라온 전체 공시 목록 가져오기
df = dart.list(start=today, end=today)

if df is not None and not df.empty:
    # 4. 주가에 영향을 주는 주요 공시 키워드로 필터링 (정규식 활용)
    # 예: 영업실적, 단일판매, 유상증자, 무상증자, 주식소각 등
    target_keywords = '실적|단일판매|증자|소각|합병|분할'
    important_reports = df[df['report_nm'].str.contains(target_keywords, regex=True)]
    
    # 5. 결과 출력 및 저장
    if not important_reports.empty:
        result_df = important_reports[['corp_name', 'report_nm', 'rcept_dt']]
        result_df.columns = ['기업명', '공시제목', '접수일자']
        print(result_df)
        
        # 기존 일정 DB(CSV)에 덧붙이기
        result_df.to_csv('dart_schedule.csv', mode='a', index=False, encoding='utf-8-sig')
else:
    print("오늘 올라온 주요 공시가 없습니다.")

```

---

### 2. 거시경제 및 글로벌 지표 (무료 경제 API)

Investing.com 같은 사이트는 봇 차단(Anti-Bot)이 매우 심해서 파이썬으로 접근하면 접속이 거부당하는 경우가 많습니다. 대신 **Financial Modeling Prep (FMP)** 같은 무료 금융 API를 사용하면 전 세계 경제 캘린더(CPI, PPI, 금리 결정 등)를 아주 깔끔한 JSON 형태로 받을 수 있습니다.

* **준비물:** FMP 사이트(site.financialmodelingprep.com) 가입 후 무료 API 키 발급
* **설치:** `pip install requests pandas`

```python
import requests
import pandas as pd
from datetime import datetime

# FMP 무료 API 키
fmp_api_key = "y3PCnQhXrf55v9fcS3FZy21H7uEYrEXA"

# 조회할 날짜 범위 설정 (오늘부터 일주일치 일정)
today = datetime.today().strftime('%Y-%m-%d')
# 파이썬 datetime의 timedelta를 이용해 7일 뒤 날짜를 구해도 됩니다.
end_date = "2026-06-23" 

url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={today}&to={end_date}&apikey={fmp_api_key}"

response = requests.get(url)
data = response.json()

# 결과를 담을 리스트
schedules = []

for item in data:
    # 시장에 영향력이 큰 '미국(US)' 지표 중, 중요도(impact)가 'High'인 것만 추출
    if item.get('country') == 'US' and item.get('impact') == 'High':
        schedules.append({
            'date': item.get('date')[:10], # 시간(Time) 자르고 날짜만
            'event': item.get('event'),
            'previous': item.get('previous'),
            'estimate': item.get('estimate')
        })

df = pd.DataFrame(schedules)
print("\n=== 이번 주 주요 미국 경제 지표 일정 ===")
print(df)
df.to_csv('macro_schedule.csv', index=False, encoding='utf-8-sig')

```

---

### 3. 정부 정책 및 학회 일정 (RSS + 로컬 LLM)

정부 부처(예: 산업통상자원부, 식약처 등) 홈페이지에는 대부분 보도자료를 실시간으로 쏴주는 **RSS 피드**가 있습니다. 이를 받아와서 본문 텍스트를 이전에 세팅했던 로컬 LLM(Ollama)에 넘겨 날짜와 일정을 추출합니다.

* **설치:** `pip install feedparser requests`

```python
import feedparser
import requests
import re

# 산업통상자원부 보도자료 RSS URL (예시)
RSS_URL = "https://www.motie.go.kr/motie/rss/press.xml"
OLLAMA_URL = "http://localhost:11434/api/generate"

print("RSS 피드 수집 중...")
feed = feedparser.parse(RSS_URL)

# 최신 5개 보도자료만 검사
for entry in feed.entries[:5]:
    title = entry.title
    summary = re.sub('<[^<]+>', '', entry.description) # HTML 태그 제거
    
    # 제목에 특정 키워드가 있을 때만 LLM 분석 (비용/시간 절약)
    if any(keyword in title for keyword in ['개최', '계획', '발표', '추진']):
        print(f"\n타겟 정책 발견: {title}")
        
        prompt = f"""
        다음 정부 보도자료 내용에서 향후 예정된 '구체적인 행사 날짜'와 '행사명/정책명'만 추출하세요.
        출력형식: YYYY-MM-DD | 행사명
        
        보도자료: {summary[:1000]}
        """
        
        payload = {"model": "gemma2:2b", "prompt": prompt, "stream": False}
        
        try:
            res = requests.post(OLLAMA_URL, json=payload, timeout=30)
            print("▶ 추출된 일정:", res.json()['response'].strip())
        except Exception as e:
            print("LLM 추출 실패:", e)

```

---

### 4. 증시 일반 일정 (웹 크롤링 기초)

신규 상장일, 보호예수 해제, 옵션만기일 같은 데이터는 네이버 금융이나 인포스탁 등의 표(Table)로 잘 정리되어 있습니다. Pandas의 `read_html`을 사용하면 복잡한 코드 없이 웹페이지의 표를 통째로 엑셀 데이터로 가져올 수 있습니다.

* **설치:** `pip install lxml pandas requests html5lib`

```python
import pandas as pd
import requests

# 예시: 특정 사이트의 공모주/증시일정 게시판 (URL은 실제 타겟 사이트에 맞게 변경 필요)
# 주의: 네이버 금융 등은 User-Agent를 확인하므로 헤더를 추가해야 봇으로 차단당하지 않습니다.
url = "가져오고자_하는_증시일정_웹페이지_URL"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    response = requests.get(url, headers=headers)
    
    # 웹페이지 HTML 안에 있는 모든 <table> 태그를 찾아서 데이터프레임 리스트로 변환
    tables = pd.read_html(response.text)
    
    # 보통 원하는 데이터는 첫 번째[0]나 두 번째[1] 표에 들어있습니다.
    target_table = tables[0] 
    
    print("\n=== 웹 크롤링으로 가져온 일정 표 ===")
    print(target_table.head())
    
except Exception as e:
    print("크롤링 에러 (사이트 구조가 변경되었거나 보안에 막혔습니다):", e)

```

### 💡 파이프라인 자동화 팁

위 4개의 파이썬 파일(`dart_api.py`, `macro_api.py`, `rss_llm.py`, `crawling.py`)을 만드신 후, 윈도우의 작업 스케줄러(Task Scheduler)를 이용해 "매일 아침 7시"에 이 스크립트들이 순차적으로 실행되도록 설정하시면 됩니다. 그러면 사용자는 아무것도 하지 않아도 매일 아침 하나의 통합된 엑셀(DB) 파일에서 오늘 장을 이끌 모든 섹터의 이벤트들을 확인할 수 있습니다.




plan 2

해외 글로벌 컨퍼런스(바이오 학회, 반도체/AI 기술 박람회 등)는 국내 증시에도 엄청난 테마 훈풍을 몰고 오는 핵심 재료입니다. (예: ASCO, ESMO, JP모건 헬스케어 컨퍼런스, CES, NVIDIA GTC, ROSCon 등)

하지만 이런 해외 일정은 중앙화된 하나의 API가 없고, 사이트마다 구조가 달라 개별 크롤링을 시도하면 유지보수 지옥에 빠집니다. 이럴 때 개발자들이 즐겨 쓰는 '비용 0원, 차단율 0%'의 가장 스마트한 모니터링 우회 전략 2가지를 알려드립니다.

전략 1. 구글 알리미(Google Alerts)를 'RSS 피드'로 변환하기 (강력 추천)
구글 API를 돈 내고 쓸 필요가 없습니다. 구글 알리미에서 내가 원하는 핵심 키워드를 등록한 뒤, 알림을 이메일이 아닌 'RSS 피드'로 받도록 설정하면 무료 전용 API가 하나 생기는 것과 같습니다.

설정 방법:

구글 알리미(google.co.kr/alerts) 접속

수집할 키워드 입력

예시: ("ASCO" OR "ESMO" OR "JP Morgan Healthcare" OR "NVIDIA GTC" OR "CES") AND ("schedule" OR "dates" OR "초록 발표" OR "컨퍼런스")

'옵션 표시' 클릭 -> '수신 위치'를 [RSS 피드]로 변경 -> 알림 만들기

원리: 이렇게 생성된 고유 RSS 링크를 파이썬 feedparser로 읽어와서, 이전에 만들어둔 로컬 LLM(Ollama)에 던져 "해외 학회 이름과 날짜만 뽑아줘"라고 시키면 됩니다.

전략 2. 글로벌 PR 배포망(Press Wire) RSS 저격하기
글로벌 기업들이나 학회 주최 측은 일정이 확정되면 무조건 PR 배포망(PR Newswire, Business Wire 등)을 통해 공식 보도자료를 뿌립니다. 이곳의 산업별(바이오, 반도체) RSS를 수집하는 것이 가장 빠르고 노이즈가 적습니다.

PR Newswire 바이오/헬스케어 피드: [https://www.prnewswire.com/rss/health-care/biotechnology-latest-news/rss.xml](https://www.prnewswire.com/rss/health-care/biotechnology-latest-news/rss.xml)

PR Newswire 테크/반도체 피드: [https://www.prnewswire.com/rss/computer-electronics/semiconductor-latest-news/rss.xml](https://www.prnewswire.com/rss/computer-electronics/semiconductor-latest-news/rss.xml)

💻 구글 알리미 RSS + 로컬 LLM 파이썬 코드
구글 알리미에서 생성한 RSS 링크를 활용해 해외 일정을 자동 수집하는 코드입니다.

Python
import feedparser
import requests
import re
from datetime import datetime
import pandas as pd

# ==========================================
# 구글 알리미에서 생성한 RSS 피드 URL을 넣으세요.
# (이 URL은 본인 계정에서 생성한 고유 링크여야 합니다)
# ==========================================
GOOGLE_ALERT_RSS_URL = "https://www.google.co.kr/alerts/feeds/13636798368499168881/16957379350988607636",
"https://www.google.co.kr/alerts/feeds/13636798368499168881/16957379350988610250",
"https://www.google.co.kr/alerts/feeds/13636798368499168881/15744183024997740381",
"https://www.google.co.kr/alerts/feeds/13636798368499168881/15744183024997736748" 
OLLAMA_URL = "http://localhost:11434/api/generate"

print("🌍 글로벌 이벤트/학회 알리미 수집 중...")
feed = feedparser.parse(GOOGLE_ALERT_RSS_URL)

schedules = []

# 최신 뉴스/웹문서 10개 검사
for entry in feed.entries[:10]:
    title = re.sub('<[^<]+>', '', entry.title) # 태그 제거
    snippet = re.sub('<[^<]+>', '', entry.description)
    
    # 제목이나 내용에 학회/전시회 관련 냄새가 날 때만 LLM 호출
    if any(keyword in title.lower() or keyword in snippet.lower() for keyword in ['conference', 'symposium', 'exhibition', 'meeting', '개최', '학회']):
        
        prompt = f"""
        당신은 글로벌 기술/바이오 일정 트래커입니다.
        아래 기사 요약본에서 '해외 학회/컨퍼런스 이름'과 '개최 날짜'를 추출해주세요.
        만약 일정이 확인되지 않으면 빈칸으로 두세요.
        
        [출력 형식]
        날짜: (예: 2026-09-15)
        행사명: (예: ESMO 유럽종양내과학회)
        
        [기사 내용]
        제목: {title}
        내용: {snippet}
        """
        
        payload = {"model": "gemma2:2b", "prompt": prompt, "stream": False, "options": {"temperature": 0.1}}
        
        try:
            res = requests.post(OLLAMA_URL, json=payload, timeout=30)
            result = res.json()['response'].strip()
            
            # 간단한 파싱
            date_info, event_info = "N/A", "N/A"
            for line in result.split('\n'):
                if line.startswith('날짜:'): date_info = line.replace('날짜:', '').strip()
                if line.startswith('행사명:'): event_info = line.replace('행사명:', '').strip()
                
            if event_info != "N/A" and event_info:
                print(f"▶ 포착 완료: [{date_info}] {event_info}")
                schedules.append({
                    "date": date_info,
                    "category": "해외학회/전시",
                    "event": event_info,
                    "source": "Google Alerts"
                })
        except Exception as e:
            print(f"LLM 분석 실패: {e}")

# 기존 DB에 추가
if schedules:
    df = pd.DataFrame(schedules)
    df.to_csv("market_schedule_db.csv", mode='a', index=False, header=False, encoding='utf-8-sig')
    print("\n✅ 성공적으로 DB에 해외 일정을 추가했습니다.")
else:
    print("\n오늘은 새로 포착된 해외 일정이 없습니다.")
💡 유지보수 꿀팁: '정적 캘린더' 병행
매년 열리는 메이저 학회는 사실 개최 월(Month)이 거의 고정되어 있습니다. (예: 1월 CES, 2~3월 MWC, 6월 ASCO).
따라서 이런 초대형 이벤트 10~20개는 파이썬 딕셔너리나 엑셀 파일에 '정적(Static) 데이터'로 미리 박아두고 매년 초 날짜만 업데이트 하는 것이 가장 마음이 편하고, 위 스크립트는 '갑작스럽게 잡힌 이벤트'나 '국내 특정 기업의 참가 소식'을 포착하는 보조 레이더로 사용하는 것이 완벽한 구조입니다.


plan3

주식 시장에서 매년 반복되는 글로벌 초대형 이벤트들은 '정해진 미래'와 같습니다. 특히 **IT/AI 신기술 박람회**와 **글로벌 3대 암학회**는 행사 1~2개월 전부터 관련 테마주들의 기대감이 선반영되며 강한 시세를 분출하는 경향이 있습니다.

말씀하신 대로, 파이썬 코드에 고정(Static) 데이터로 넣어두고 매년 초 날짜만 살짝 업데이트해서 쓰기 좋은 '월별 핵심 글로벌 이벤트 캘린더'를 정리해 드립니다.

---

### 🗓️ 글로벌 핵심 박람회 & 바이오 학회 월별 캘린더

#### ❄️ 1분기 (연초 기대감 집중 구간)

연초는 1년 치 기술 트렌드와 바이오 기업들의 빅딜(M&A, 기술수출) 방향성이 결정되는 가장 중요한 시기입니다.

* **1월**
* **CES (국제전자제품박람회):** `[IT / AI / 로봇 / 자율주행]` 세계 최대 기술 전시회. 연초 로봇, AI, 메타버스 테마를 주도하는 가장 강력한 재료입니다.
* **JPMHC (JP모건 헬스케어 컨퍼런스):** `[BIO]` 전 세계 제약/바이오 기업들이 모여 기술수출(L/O) 및 파트너십을 논의하는 자리로, 바이오 섹터 연초 랠리의 핵심입니다.


* **2월**
* **MWC (모바일 월드 콩그레스):** `[통신 / AI / 스마트기기]` 모바일과 통신(6G 등) 중심의 전시회로, 최근에는 온디바이스 AI 관련 재료가 많이 쏟아집니다.


* **3월**
* **NVIDIA GTC (엔비디아 개발자 컨퍼런스):** `[반도체 / AI / 로봇]` 글로벌 AI 대장주 엔비디아의 신제품과 비전이 발표되는 행사로, 국내 반도체(HBM) 및 AI 섹터에 직접적인 타격을 줍니다. (보통 3월경 개최)
* **AACR (미국암연구학회) 초록 발표:** `[BIO]` 4월 본 행사에 앞서 초록(연구 요약본)이 3월 초중순에 공개됩니다. 이때부터 관련 파이프라인을 가진 기업들의 주가가 들썩입니다.



#### 🌱 2분기 (바이오 전성기 및 빅테크 이벤트)

글로벌 최대 규모의 종양학회와 빅테크 기업들의 소프트웨어/AI 전략이 발표되는 시기입니다.

* **4월**
* **AACR (미국암연구학회) 본행사:** `[BIO]` 전임상(동물실험) 및 초기 임상 데이터가 주로 발표됩니다.
* **하노버 메세 (Hannover Messe):** `[로봇 / 스마트팩토리]` 세계 최대 산업 박람회로, 로봇 및 공장 자동화 테마에 영향을 줍니다.


* **5월**
* **ASCO (미국임상종양학회) 초록 발표:** `[BIO]` 글로벌 3대 암학회 중 가장 권위 있는 ASCO의 초록이 공개되며, 임상 파이프라인의 가치가 재평가됩니다.


* **6월**
* **ASCO (미국임상종양학회) 본행사:** `[BIO]` 실질적인 임상 결과가 발표되는 바이오 섹터 최대 축제입니다.
* **BIO USA (바이오 인터내셔널 컨벤션):** `[BIO]` 세계 최대 바이오 파트너링 행사로, CDMO(위탁개발생산) 및 기술수출 논의가 활발합니다.
* **Apple WWDC (애플 세계 개발자 회의):** `[IT / 메타버스 / AI]` 애플의 소프트웨어 생태계 및 신규 기기(XR 등) 비전이 발표되며 관련 부품주들이 반응합니다.



#### ☀️ 3분기 (하반기 모멘텀의 시작)

주춤했던 IT 하드웨어/게임 쇼가 열리며, 하반기 유럽 지역의 큰 학회들이 대기하고 있습니다.

* **7월**
* **SIGGRAPH (시그라프):** `[메타버스 / 그래픽 / AI]` 컴퓨터 그래픽스 기술 행사로, 엔비디아 등 빅테크의 메타버스/비전 AI 기술이 공개됩니다. (7월 말~8월 초)


* **8월**
* **Gamescom (게임스컴):** `[게임 / IP]` 유럽 최대 게임 쇼. 국내 게임사들의 하반기~내년도 신작 트레일러가 공개되며 모멘텀을 형성합니다.
* **ESMO (유럽종양내과학회) 초록 발표:** `[BIO]` 하반기 바이오 최대 이벤트인 ESMO의 연구 결과가 미리 공개됩니다.


* **9월**
* **IFA (유럽 가전전시회):** `[IT / 가전 / 로봇]` 하반기 IT 신제품(특히 스마트홈, 가전 로봇) 트렌드를 엿볼 수 있습니다.
* **ESMO (유럽종양내과학회) 본행사:** `[BIO]` 하반기 바이오 투심을 결정짓는 핵심 행사입니다.
* **WCLC (세계폐암학회):** `[BIO]` 폐암 관련 신약 파이프라인을 보유한 기업들에게 매우 중요한 학회입니다.



#### 🍂 4분기 (의료기기 및 면역/혈액암 포커스)

연말을 장식하는 타겟형 바이오 학회와 내년도 트렌드를 엿볼 수 있는 발표들이 이어집니다.

* **10월**
* **SITC (면역항암학회) 초록 발표:** `[BIO]` 차세대 항암제로 꼽히는 면역항암제 관련 임상 결과가 공개됩니다.


* **11월**
* **SITC (면역항암학회) 본행사:** `[BIO]` 면역항암제, 이중항체 등 최신 바이오 트렌드 기업들이 부각됩니다.
* **RSNA (북미방사선학회):** `[의료AI / 영상기기]` 루닛, 뷰노 등 국내 의료 AI 기업들이 대거 참여하여 성과를 입증하는 핵심 무대입니다.


* **12월**
* **ASH (미국혈액학회):** `[BIO]` 백혈병, 림프종 등 혈액암 분야 최대 학회입니다.
* **SABCS (산안토니오 유방암 심포지엄):** `[BIO]` 유방암 분야 신약 파이프라인 모멘텀이 발생합니다.



---

### 💡 파이썬 자동화 스크립트 적용 팁

앞서 짜드렸던 파이썬 스크립트(구글 알리미/RSS 연동)와 함께 사용하실 때는 다음과 같은 전략이 좋습니다.

1. **정적 데이터베이스 화:** 위 리스트를 `market_events_static.csv` 같은 파일로 만들어 두고, 매년 1월 1일에 구글 검색을 통해 해당 연도의 정확한 일자(예: 2026년 CES 1.6~1.9)만 업데이트합니다.
2. **이중 체크 (크로스 체킹):** 매일 아침 구동되는 파이썬 스크립트가 위 정적 캘린더를 함께 읽어와서, "오늘부터 딱 한 달(30일) 남은 글로벌 행사"를 아침 리포트 최상단에 D-Day와 함께 띄워주도록 코드를 한 줄 추가하면 완벽한 선취매 트래킹 봇이 완성됩니다.


plan4

네, 완벽하게 가능합니다! 지금 구상하신 아이디어가 바로 여의도 퀀트 랩실이나 전문 트레이더들이 구축하는 '개인화된 투자 대시보드(Data Pipeline & Dashboard)'의 정확한 아키텍처입니다.

지금까지 만든 파이썬 스크립트들을 각각의 '수집 에이전트'로 삼고, 이를 모아 하나의 웹페이지로 구워내는(Baking) 과정은 매우 현실적이고 유지보수하기도 좋습니다.

다만, 한 가지 **핵심적인 기술적 우회로**가 필요합니다.

---

### 🚨 아키텍처 설계 시 주의점: 로컬 LLM의 한계

GitHub에서 제공하는 무료 서버(GitHub Actions)를 사용해 매일 자동으로 스크립트를 돌릴 수 있습니다. 하지만, 우리가 앞서 설계한 방식에는 로컬 PC에 설치된 Ollama(gemma2 등)가 포함되어 있습니다. GitHub 서버는 우리 집 PC에 있는 Ollama에 접속할 수 없습니다.

따라서 **"실행은 내 PC에서, 결과물 전시만 GitHub에서"** 하는 하이브리드 방식을 구축해야 완벽한 무료 자동화가 완성됩니다.

---

### 🛠️ 나만의 퀀트 대시보드 구축 3단계 파이프라인

#### 1단계: 에이전트(Agent) 모듈화 및 통합 (Data Aggregation)

앞서 만든 5개의 스크립트가 각각 데이터를 수집한 뒤, 최종적으로 `master_schedule_db.csv`라는 하나의 마스터 파일로 데이터를 밀어 넣도록 세팅합니다.

* Agent 1: DART 공시 수집기
* Agent 2: 글로벌 매크로 지표 수집기
* Agent 3: 네이버 증시일정 크롤러
* Agent 4: RSS + 로컬 LLM (정부 정책/해외 학회 요약)
* Agent 5: 정적 캘린더 (미리 하드코딩해 둔 글로벌 박람회)

#### 2단계: 웹 퍼블리셔 에이전트 (HTML Generator)

파이썬이 마스터 CSV 파일을 읽어서, 예쁘게 디자인된 HTML 파일(`index.html`)로 변환해 주는 스크립트를 하나 추가합니다. 복잡한 웹 서버(Django, Node.js)를 띄울 필요 없이, 파이썬으로 HTML 텍스트를 만들어 저장만 하면 됩니다.

#### 3단계: GitHub Pages 자동 배포 (Git Push Automation)

내 PC의 작업 스케줄러가 매일 아침 7시에 1~2단계를 모두 끝내면, 마지막으로 완성된 `index.html`을 내 GitHub 저장소로 자동 `Push` 합니다. 그러면 전 세계 어디서든 모바일로 접속 가능한 **나만의 주식 일정 웹사이트**가 매일 아침 갱신됩니다.

---

### 💻 2단계: 파이썬으로 웹페이지(HTML) 자동 생성하기

수집된 CSV 데이터를 모바일에서도 보기 편한 깔끔한 웹페이지로 만들어주는 파이썬 코드입니다. (Bootstrap CSS를 적용하여 디자인을 자동화합니다.)

```python
import pandas as pd
from datetime import datetime

def generate_dashboard():
    # 1. 통합된 마스터 DB 읽기
    try:
        df = pd.read_csv("master_schedule_db.csv")
        # 날짜순으로 정렬
        df = df.sort_values(by='date') 
    except FileNotFoundError:
        print("DB 파일이 없습니다.")
        return

    today = datetime.today().strftime('%Y-%m-%d')
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 2. HTML 테이블 행(Row) 생성
    table_rows = ""
    for _, row in df.iterrows():
        # 오늘 일정은 빨간색으로 하이라이트
        highlight = "table-danger" if row['date'] == today else ""
        
        table_rows += f"""
        <tr class="{highlight}">
            <td><strong>{row['date']}</strong></td>
            <td><span class="badge bg-primary">{row['category']}</span></td>
            <td>{row['event']}</td>
            <td><small class="text-muted">{row.get('source', 'System')}</small></td>
        </tr>
        """

    # 3. HTML 템플릿에 데이터 삽입 (Bootstrap 5 적용)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>시장 주도 테마 & 일정 대시보드</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h2>📈 마켓 모멘텀 & 일정 대시보드</h2>
                <span class="badge bg-secondary">최근 업데이트: {update_time}</span>
            </div>
            
            <div class="card shadow-sm">
                <div class="card-body">
                    <table class="table table-hover align-middle">
                        <thead class="table-dark">
                            <tr>
                                <th scope="col">날짜</th>
                                <th scope="col">섹터/분류</th>
                                <th scope="col">핵심 모멘텀 일정</th>
                                <th scope="col">출처</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # 4. index.html 파일로 저장
    with open("index.html", "w", encoding="utf-8") as file:
        file.write(html_content)
        
    print("✅ 성공적으로 대시보드 웹페이지(index.html)가 생성되었습니다.")

if __name__ == "__main__":
    generate_dashboard()

```

### 💻 3단계: 파이썬으로 GitHub 자동 업로드 (Auto Push)

파이썬 스크립트가 실행될 때마다 GitHub로 알아서 결과물을 올리는 코드입니다. (사전에 Git이 설치되어 있고 저장소가 세팅되어 있어야 합니다.)

```python
import os
import subprocess

def git_push_automation():
    print("🔄 GitHub Pages 배포를 시작합니다...")
    
    # 깃허브 업로드 명령어 순차 실행
    commands = [
        ["git", "add", "index.html"],
        ["git", "commit", "-m", "Auto-update daily market schedule"],
        ["git", "push", "origin", "main"]
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"성공: {' '.join(cmd)}")
        except subprocess.CalledProcessError as e:
            print(f"에러 발생 ({' '.join(cmd)}): {e.stderr}")
            break

if __name__ == "__main__":
    git_push_automation()

```

---

이러한 시스템을 "정적 사이트 생성(SSG) 기반의 데이터 파이프라인"이라고 부릅니다. 서버 호스팅 비용(AWS 등)을 매달 낼 필요 없이, 데이터 수집부터 웹페이지 배포까지 100% 무료로 자동화할 수 있는 가장 스마트한 방법입니다.

이 전체 파이프라인 중에서 가장 먼저 세팅을 시도해 보고 싶으신 에이전트(예: DART 공시, 글로벌 지표, 또는 HTML 페이지 뼈대 만들기)가 있으신가요?
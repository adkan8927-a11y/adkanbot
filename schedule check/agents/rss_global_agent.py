import feedparser
import requests
import re
import time
from datetime import datetime, timedelta

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:e4b"

def get_global_schedules():
    GLOBAL_RSS_SOURCES = [
        # 구글 알리미 피드 4종
        {"url": "https://www.google.co.kr/alerts/feeds/13636798368499168881/16957379350988607636", "name": "Google Alerts 1"},
        {"url": "https://www.google.co.kr/alerts/feeds/13636798368499168881/16957379350988610250", "name": "Google Alerts 2"},
        {"url": "https://www.google.co.kr/alerts/feeds/13636798368499168881/15744183024997740381", "name": "Google Alerts 3"},
        {"url": "https://www.google.co.kr/alerts/feeds/13636798368499168881/15744183024997736748", "name": "Google Alerts 4"},
        
        # PR Newswire 피드 2종
        {"url": "https://www.prnewswire.com/rss/health-care/biotechnology-latest-news/rss.xml", "name": "PR Newswire Bio"},
        {"url": "https://www.prnewswire.com/rss/computer-electronics/semiconductor-latest-news/rss.xml", "name": "PR Newswire Tech"}
    ]
    
    schedules = []
    fifteen_days_ago = datetime.today() - timedelta(days=15)
    
    for source in GLOBAL_RSS_SOURCES:
        url = source["url"]
        name = source["name"]
        print(f"📥 [해외학회/전시] {name} RSS 수집 중...")
        
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"❌ 글로벌 RSS 파싱 에러 ({name}): {e}")
            continue
            
        for entry in feed.entries[:5]: # 소스별 최신 5개씩 검사
            # 15일 이내 자료 필터링
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if pub_dt < fifteen_days_ago:
                        continue # 15일 이전 기사는 스킵
                except Exception as e:
                    print(f"⚠️ 날짜 파싱 실패: {e}")
                    
            title = re.sub('<[^<]+>', '', entry.title) if hasattr(entry, 'title') else ""
            snippet = re.sub('<[^<]+>', '', entry.description) if hasattr(entry, 'description') else ""
            
            # 학회/전시회/발표 관련 핵심 키워드 체크
            if any(keyword in title.lower() or keyword in snippet.lower() for keyword in ['conference', 'symposium', 'exhibition', 'meeting', 'seminar', 'summit', '개최', '학회', '박람회', '발표회']):
                prompt = f"""당신은 글로벌 기술 및 바이오 일정 분석기입니다.
아래 뉴스 요약본에서 '해외 학회/컨퍼런스/행사 이름'과 '개최 날짜(YYYY-MM-DD)'를 추출해 주세요.

[출력 규칙]
1. 반드시 한 줄로 "날짜: YYYY-MM-DD | 행사명: [내용]" 포맷으로만 출력하세요.
2. 일정이 구체적이지 않거나 확인되지 않는다면 아무것도 출력하지 마세요 (빈 응답).
3. 다른 서론이나 꼬리표는 일절 금지합니다.

기사 제목: {title}
기사 내용: {snippet}
"""
                headers = {"Content-Type": "application/json"}
                data = {
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": "You are a precise database compiler."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }
                
                try:
                    response = requests.post(OLLAMA_URL, headers=headers, json=data, timeout=120)
                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        
                        date_val, event_val = None, None
                        match = re.search(r'날짜:\s*([\d\-]+).*행사명:\s*(.+)', content)
                        if match:
                            date_val = match.group(1).strip()
                            event_val = match.group(2).strip()
                        else:
                            for line in content.split('\n'):
                                if '날짜' in line:
                                    date_val = line.split('날짜:')[-1].replace('|', '').strip()
                                if '행사명' in line:
                                    event_val = line.split('행사명:')[-1].strip()
                                    
                        if date_val and event_val:
                            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_val):
                                schedules.append({
                                    "date": date_val,
                                    "category": "해외학회/전시",
                                    "event": event_val,
                                    "source": name
                                })
                except Exception as e:
                    print(f"❌ 글로벌 LLM 추출 에러: {e}")
                    
    return schedules

if __name__ == "__main__":
    res = get_global_schedules()
    print("글로벌 수집 완료:", len(res), "건 수집됨")

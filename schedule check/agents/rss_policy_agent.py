import feedparser
import requests
import re

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:e4b"

def get_policy_schedules():
    RSS_URL = "https://www.motie.go.kr/motie/rss/press.xml"
    schedules = []
    
    try:
        feed = feedparser.parse(RSS_URL)
    except Exception as e:
        print(f"❌ 정책 RSS 파싱 에러: {e}")
        return []
        
    import time
    from datetime import datetime, timedelta
    
    fifteen_days_ago = datetime.today() - timedelta(days=15)
    
    for entry in feed.entries:
        # 15일 이내 자료 필터링
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                if pub_dt < fifteen_days_ago:
                    continue # 15일 이전 자료는 스킵
            except Exception as e:
                print(f"⚠️ 날짜 파싱 실패: {e}")
                
        title = entry.title
        summary = re.sub('<[^<]+>', '', entry.description) if hasattr(entry, 'description') else ""
        
        if any(keyword in title for keyword in ['개최', '계획', '발표', '추진', '세미나', '포럼']):
            prompt = f"""다음 정부 보도자료 내용에서 향후 예정된 구체적인 '행사 날짜'와 '행사명'을 추출하세요.
출력형식은 오직 한 줄로 "날짜: YYYY-MM-DD | 행사명: [내용]" 포맷으로만 출력하세요.
다른 미사여구나 추가 설명은 절대 제외하세요.

보도자료 제목: {title}
보도자료 요약: {summary[:800]}
"""
            headers = {"Content-Type": "application/json"}
            data = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are a precise data extractor."},
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
                        # 날짜가 YYYY-MM-DD 형식인지 체크 후 추가
                        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_val):
                            schedules.append({
                                "date": date_val,
                                "category": "정부정책",
                                "event": event_val,
                                "source": "산업부 RSS"
                            })
            except Exception as e:
                print(f"❌ 정책 LLM 추출 에러: {e}")
                
    return schedules

if __name__ == "__main__":
    res = get_policy_schedules()
    print("정책 수집 결과:", res)

import feedparser
import requests
import re
import time
from datetime import datetime, timedelta

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:e4b"

def get_policy_schedules():
    POLICY_RSS_FEEDS = {
        "과기부": "https://www.msit.go.kr/user/rss/rss.do?bbsSeqNo=67",
        "식약처": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0021",
        "복지부": "https://www.mohw.go.kr/rss/board.es?mid=a10503000000&bid=0027",
        "금융위": "http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111",
        "국토부": "https://www.molit.go.kr/dev/board/board_rss.jsp?rss_id=N01_B",
        "산업부": "https://www.motie.go.kr/motie/rss/press.xml",
        "문체부": "http://www.mcst.go.kr/common/rss/press.jsp",
        # 구글 알리미 - 정부정책 관련
        "정책알리미1": "https://www.google.com/alerts/feeds/13636798368499168881/8203039951955249401",
        "정책알리미2": "https://www.google.com/alerts/feeds/13636798368499168881/10383779406087198489",
    }
    
    schedules = []
    fifteen_days_ago = datetime.today() - timedelta(days=15)
    
    for dept_name, url in POLICY_RSS_FEEDS.items():
        print(f"📥 [정부정책] {dept_name} RSS 수집 중...")
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"❌ {dept_name} RSS 파싱 에러: {e}")
            continue
            
        for entry in feed.entries[:5]: # 부처별 최신 5개씩 검사
            # 15일 이내 자료 필터링
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if pub_dt < fifteen_days_ago:
                        continue # 15일 이전 자료는 스킵
                except Exception as e:
                    print(f"⚠️ {dept_name} 날짜 파싱 실패: {e}")
            
            title = entry.title
            summary = re.sub('<[^<]+>', '', entry.description) if hasattr(entry, 'description') else ""
            
            # 행사/일정 관련 핵심 키워드 매칭
            if any(keyword in title for keyword in ['개최', '계획', '발표', '추진', '세미나', '포럼', '공청회', '회의', '간담회']):
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
                            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_val):
                                schedules.append({
                                    "date": date_val,
                                    "category": "정부정책",
                                    "event": f"[{dept_name}] {event_val}",
                                    "source": f"{dept_name} RSS"
                                })
                except Exception as e:
                    print(f"❌ {dept_name} LLM 추출 에러: {e}")
                    
    return schedules

if __name__ == "__main__":
    res = get_policy_schedules()
    print("정책 수집 완료:", len(res), "건 수집됨")

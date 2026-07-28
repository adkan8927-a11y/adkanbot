import feedparser
import time
from datetime import datetime, timedelta

POLICY_RSS_FEEDS = {
    "과기부": "https://www.msit.go.kr/user/rss/rss.do?bbsSeqNo=67",
    "금융위": "http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111",
    "정책알리미1": "https://www.google.com/alerts/feeds/13636798368499168881/8203039951955249401",
    "정책알리미2": "https://www.google.com/alerts/feeds/13636798368499168881/10383779406087198489",
}

fifteen_days_ago = datetime.today() - timedelta(days=60)

for dept_name, url in POLICY_RSS_FEEDS.items():
    print(f"\n========================================")
    print(f"📥 [테스트] {dept_name} ({url}) 수집 시작...")
    print(f"========================================")
    try:
        feed = feedparser.parse(url)
        print(f"성공적으로 파싱함. 피드 제목: '{feed.feed.get('title', 'N/A')}', 총 엔트리 수: {len(feed.entries)}")
        
        for idx, entry in enumerate(feed.entries[:5]):
            print(f"\n  [{idx+1}] 제목: {entry.title}")
            print(f"      링크: {entry.link}")
            
            # 날짜 파싱 테스트
            pub_dt = "N/A"
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    is_recent = pub_dt >= fifteen_days_ago
                    print(f"      발행일: {pub_dt} (최근 15일 이내 여부: {is_recent})")
                except Exception as e:
                    print(f"      ⚠️ 날짜 변환 에러: {e}")
            else:
                print(f"      ⚠️ published_parsed 속성 없음")
                
            # description/summary 파싱 테스트
            desc = entry.get('description', entry.get('summary', ''))
            print(f"      본문 요약(일부): {desc[:100]}...")
            
    except Exception as e:
        print(f"❌ {dept_name} 에러 발생: {e}")

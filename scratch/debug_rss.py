import feedparser
import time
from datetime import datetime, timedelta

POLICY_RSS_FEEDS = {
    "과기부": "https://www.msit.go.kr/user/rss/rss.do?bbsSeqNo=67",
    "식약처": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0021",
    "복지부": "https://www.mohw.go.kr/rss/board.es?mid=a10503000000&bid=0027",
    "금융위": "http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111",
    "국토부": "https://www.molit.go.kr/dev/board/board_rss.jsp?rss_id=N01_B",
    "산업부": "https://www.motie.go.kr/motie/rss/press.xml",
    "문체부": "http://www.mcst.go.kr/common/rss/press.jsp"
}

fifteen_days_ago = datetime.today() - timedelta(days=15)

for dept_name, url in POLICY_RSS_FEEDS.items():
    print(f"\n📂 [{dept_name}] RSS 최근 데이터 점검")
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            print("  ⚠️ 수집된 엔트리가 아예 없습니다.")
            continue
        for entry in feed.entries[:3]:
            pub_dt_str = "날짜 없음"
            is_recent = "X"
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                pub_dt_str = pub_dt.strftime('%Y-%m-%d')
                is_recent = "O" if pub_dt >= fifteen_days_ago else "X"
            
            title = entry.title
            has_keyword = "O" if any(keyword in title for keyword in ['개최', '계획', '발표', '추진', '세미나', '포럼', '공청회', '회의', '간담회']) else "X"
            print(f"  - 제목: {title}")
            print(f"    발행일: {pub_dt_str} (15일 이내 여부: {is_recent}) | 키워드 매칭 여부: {has_keyword}")
    except Exception as e:
        print(f"  ❌ 에러 발생: {e}")

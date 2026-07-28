import feedparser
import re

POLICY_RSS_FEEDS = {
    "과기부": "https://www.msit.go.kr/user/rss/rss.do?bbsSeqNo=67",
    "식약처": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0021",
    "복지부": "https://www.mohw.go.kr/rss/board.es?mid=a10503000000&bid=0027",
    "금융위": "http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111",
    "국토부": "https://www.molit.go.kr/dev/board/board_rss.jsp?rss_id=N01_B",
    "산업부": "https://www.motie.go.kr/motie/rss/press.xml",
    "문체부": "http://www.mcst.go.kr/common/rss/press.jsp"
}

for dept, url in POLICY_RSS_FEEDS.items():
    print(f"\n[{dept}]")
    try:
        feed = feedparser.parse(url)
        print(f"Total entries: {len(feed.entries)}")
        for e in feed.entries[:3]:
            print("Title:", e.title)
    except Exception as ex:
        print("Error:", ex)

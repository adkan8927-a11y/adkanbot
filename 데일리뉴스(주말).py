import os
import sys
import json
import urllib.request
import requests
import re
from datetime import datetime, timedelta, timezone
import time
import subprocess

try:
    import feedparser
except ImportError:
    print("⚡ feedparser 라이브러리 자동 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser"])
    import feedparser

# ==========================================
# 해외 RSS 피드 목록
# ==========================================
FOREIGN_RSS_FEEDS = [
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.bloomberg.com/technology/news.rss",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "https://www.ft.com/rss/home/us",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://seekingalpha.com/market_currents.xml",
]

try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    print("⚡ sentence-transformers 또는 torch 라이브러리 자동 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "torch"])
    from sentence_transformers import SentenceTransformer, util
    import torch

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID") or "pgpbMmGVrHyECNJtvIG1"
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET") or "AJjwBxBc7f"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6KJkRvIzeRwbeHGxOMik8zALM8AD3nZsXuse392Gle_cQ"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or ""
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or ""

KEYWORDS_JSON_PATH = "키워드3.json"

SIMILARITY_THRESHOLD = 0.57  # 유사도 임계치
DEDUP_THRESHOLD = 0.82       # 중복 제거 임계치
TOP_N_NEWS = 5               # 섹터별 최대 기사 노출 건수

print("🧠 로컬 임베딩 모델 로딩 중 (jhgan/ko-sroberta-multitask)...")
try:
    embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    print("✅ 임베딩 모델 로딩 완료.")
except Exception as e:
    print(f"❌ 임베딩 모델 로딩 실패: {e}")
    sys.exit(1)

def load_and_embed_keywords():
    if not os.path.exists(KEYWORDS_JSON_PATH):
        print(f"❌ 에러: {KEYWORDS_JSON_PATH} 파일이 존재하지 않습니다.")
        sys.exit(1)
    with open(KEYWORDS_JSON_PATH, "r", encoding="utf-8") as f:
        keyword_db = json.load(f)
    embedded_db = {}
    for sector, keywords in keyword_db.items():
        if not keywords:
            embedded_db[sector] = {"keywords": [], "embeddings": None}
            continue
        embeddings = embed_model.encode(keywords, convert_to_tensor=True)
        embedded_db[sector] = {
            "keywords": keywords,
            "embeddings": embeddings
        }
    return embedded_db

KEYWORD_EMBEDDED_DB = load_and_embed_keywords()

def send_telegram_alert(summary_text, report_date, report_type="주말"):
    """생성된 요약본의 주요 헤드라인과 GitHub Pages 링크를 텔레그램으로 알림합니다."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없어서 알림 전송을 건너뜁니다.")
        return
        
    github_user = os.environ.get("GITHUB_ACTOR", "adkan")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "daily-news-crawler").split("/")[-1]
    
    if report_type == "장전":
        file_name = f"reports/{report_date}_장전.html"
    elif report_type == "장후":
        file_name = f"reports/{report_date}_장후.html"
    else:
        file_name = f"reports/{report_date}_주말.html"
        
    report_url = f"https://{github_user}.github.io/{github_repo}/{file_name}"
    
    message = f"🔔 [데일리뉴스 ({report_type}) 발행 완료]\n\n"
    message += f"📅 기준 시각: {report_date}\n"
    message += f"🔗 웹 리포트 보기: {report_url}\n\n"
    message += f"📝 주요 시황 요약 (일부):\n"
    
    # 텔레그램 한도(4096자) 및 가독성을 고려해 앞부분 800자만 추출
    message += summary_text[:800] + "\n..."
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ 텔레그램 알림 전송 성공!")
        else:
            print(f"❌ 텔레그램 전송 실패: {response.text}")
    except Exception as e:
        print(f"⚠️ 텔레그램 전송 오류: {e}")

def collect_foreign_rss(start_time, end_time, max_per_feed=30):
    print(f"\n🌐 해외 RSS 수집 시작 ({len(FOREIGN_RSS_FEEDS)}개 피드)...")
    collected = []
    seen_links = set()
    start_utc = start_time.replace(tzinfo=timezone.utc) - timedelta(hours=9)
    end_utc = end_time.replace(tzinfo=timezone.utc) - timedelta(hours=9)
    for feed_url in FOREIGN_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries:
                if count >= max_per_feed:
                    break
                link = entry.get("link", "")
                if not link or link in seen_links:
                    continue
                pub_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                if pub_time and (pub_time < start_utc or pub_time > end_utc):
                    continue
                title = entry.get("title", "").strip()
                desc = re.sub(r'<[^>]+>', '', entry.get("summary", "")).strip()
                if not title:
                    continue
                seen_links.add(link)
                collected.append({
                    "title": title,
                    "link": link,
                    "desc": desc[:300] if desc else "",
                    "pub_time": pub_time.strftime("%Y-%m-%d %H:%M:%S") if pub_time else "unknown",
                    "matched_keyword": "해외 RSS",
                    "score": 1.0,
                    "is_foreign": True
                })
                count += 1
        except Exception as e:
            print(f"  ⚠️ RSS 수집 실패 ({feed_url}): {e}")
    print(f"✅ 해외 RSS 수집 완료: 총 {len(collected)}건")
    return collected

def translate_foreign_titles_gemini(news_list):
    if not news_list:
        return news_list
    print(f"🔤 영문 기사 제목 {len(news_list)}건 한국어 번역 중 (Gemini)...")
    titles_numbered = "\n".join([f"{i+1}. {n['title']}" for i, n in enumerate(news_list)])
    prompt = f"""다음 영문 뉴스 제목들을 한국 주식/경제 시황 맥락에 맞는 자연스러운 한국어로 번역하세요.
번역 규칙:
- 회사명·인명은 한국 통용 표기 사용 (NVIDIA→엔비디아, Fed→연방준비제도, Trump→트럼프 등)
- 번역문만 번호 순서대로 출력하고 설명·원문은 포함하지 마세요.

{titles_numbered}"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096
        }
    }
    max_retries = 3
    base_delay = 5
    translated_titles = []
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                translated_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            for line in translated_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                cleaned = re.sub(r'^\d+[\.\.\)\s]+', '', line).strip()
                if cleaned:
                    translated_titles.append(cleaned)
            break
        except Exception as e:
            print(f"⚠️ Gemini 번역 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
    if translated_titles:
        for i, news in enumerate(news_list):
            if i < len(translated_titles) and translated_titles[i]:
                news["title_original"] = news["title"]
                news["title"] = translated_titles[i]
    return news_list

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text).replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

def get_naver_news(keyword, start_time, end_time, max_news=100, require_digit=False):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    news_list = []
    seen_links = set()
    reached_past_limit = False
    for start_idx in range(1, 1001, 100):
        if reached_past_limit or len(news_list) >= max_news:
            break
        params = {"query": keyword, "display": 100, "start": start_idx, "sort": "date"}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                break
            items = response.json().get('items', [])
            if not items:
                break
            for item in items:
                pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S +0900')
                if pub_date < start_time:
                    reached_past_limit = True
                    break
                if pub_date > end_time:
                    continue
                link = item.get('link', '')
                if link in seen_links:
                    continue
                title = clean_html(item.get('title', ''))
                if require_digit and not re.search(r'\d', title):
                    continue
                desc = clean_html(item.get('description', ''))
                seen_links.add(link)
                news_list.append({
                    "title": title,
                    "link": link,
                    "desc": desc,
                    "pub_time": pub_date.strftime("%Y-%m-%d %H:%M:%S")
                })
                if len(news_list) >= max_news:
                    break
        except Exception as e:
            print(f"네이버 API 수집 중 예외 발생 ({keyword}): {e}")
            break
    return news_list
# ==========================================
# 섹터별 앵커 키워드 게이트
# 키워드3.json의 각 섹터 키워드에서 자주 등장하는 핵심 단어를 추출해 제목에 하나도 없으면 기타로 강제 이동
# ==========================================
SECTOR_ANCHOR_KEYWORDS = {
    "반도체": ["반도체", "삼성전자", "SK하이닉스", "HBM", "D램", "낙드", "웨이퍼", "파운드리", "EUV", "CXL", "메모리", "소부장"],
    "자동차": ["자동차", "전기차", "EV", "하이브리드", "현대차", "기아", "완성차", "IRA", "자율주행", "모비스", "V2G", "FSD"],
    "이차전지": ["배터리", "이차전지", "전고체", "LG에너지", "삼성SDI", "SK온", "양극재", "음극재", "동박", "ESS", "LFP", "첨단배터리"],
    "전력 / 에너지": ["에너지", "원전", "태양광", "풍력", "전력", "한수원", "SMR", "변압기", "송배전", "수소", "신재생", "케이블"],
    "AI / 로봇": ["AI", "인공지능", "로봇", "휴머노이드", "LLM", "GPU", "데이터센터", "에이전튱", "ChatGPT", "생성형"],
    "IT / 신기술": ["데이터센터", "양자", "사이버보안", "OLED", "디스플레이", "핀테크", "간편결제", "XR", "블록체인", "앱마켓"],
    "BIO / 의료AI": ["바이오", "신약", "임상", "치료제", "FDA", "의료AI", "항암", "자가면역", "비만", "바이오시밀러", "제약", "의료기기"],
    "조선 / 해운": ["조선", "해운", "선박", "LNG선", "컨테이너선", "함정", "잠수함", "MRO", "컨테이너", "운임"],
    "우주 / 항공": ["우주", "항공", "위성", "스페이스X", "UAM", "드론", "스타링크", "스타쉽"],
    "코인 / STO": ["코인", "비트코인", "STO", "토큰증권", "가상자산", "알트코인", "리플", "ETF", "스테이블코인"],
    "IP / 엔터": ["K-팝", "아이돌", "엔터테인먼트", "게임", "콘텐츠", "OTT", "넷플릭스", "웹툰"],
    "건설 / 인프라": ["건설", "인프라", "재건축", "수주", "시공사", "PF", "네옴시티", "재개발", "미분양", "아파트"],
    "국방 / 방산": ["방산", "K-방산", "무기", "K2전차", "K9자주포", "미사일", "잠수함", "NATO", "한화", "현대로템", "군함", "방위"],
    "M\u0026A / 주요 공시": ["무상증자", "자사주", "IPO", "상장", "M\u0026A", "지분", "유상증자", "실적", "어닝", "주주환원", "회사채", "ADR"],
    "해외 이슈": ["다우", "나스닥", "S&P", "Fed", "FOMC", "엔비디아", "마이크론", "애플", "구글", "마이크로소프트"],
}

def validate_anchor_keyword(title, sector):
    """제목(title)에 해당 섹터의 앵커 키워드가 하나도 없으면 False 반환"""
    anchors = SECTOR_ANCHOR_KEYWORDS.get(sector)
    if not anchors:
        return True
    title_lower = title.lower()
    return any(a.lower() in title_lower for a in anchors)

def check_and_adjust_sector(news, sector):
    title = news["title"].lower()
    desc = news["desc"].lower()
    full_text = title + " " + desc
    if sector == "국제 - 미국":
        domestic_market_terms = ["코스피", "코스닥", "한은", "한국은행", "국민연금", "금통위", "금융위", "금감원", "국내 증시", "한국 증시", "코스피지수", "코스닥지수", "국내 주식", "한국 주식"]
        domestic_regions = [
            "경기도", "경기", "천안", "아산", "춘천", "안양", "수원", "용인", "성남", "고양", "화성", 
            "부천", "남양주", "안산", "평택", "안성", "시흥", "파주", "의정부", "김포", "광주", "광명", 
            "군포", "하남", "오산", "이천", "양주", "구리", "포천", "의왕", "여주", "동두천", "과천", 
            "가평", "양평", "연천", "인천", "강원", "원주", "강릉", "동해", "태백", "속초", "삼척", 
            "홍천", "횡성", "영월", "평창", "정선", "철원", "화천", "양구", "인제", "고성", "양양", 
            "충북", "청주", "충주", "제천", "보은", "옥천", "영동", "증평", "진천", "괴산", "음성", 
            "단양", "충남", "공주", "보령", "서산", "논산", "계룡", "당진", "금산", "부여", "서천", 
            "청양", "홍성", "예산", "태안", "전북", "전주", "군산", "익산", "정읍", "남원", "김제", 
            "완주", "진안", "무주", "장수", "임실", "순창", "고창", "부안", "전남", "목포", "여수", 
            "순천", "나주", "광양", "담양", "곡성", "구례", "고흥", "보성", "화순", "장흥", "강진", 
            "해남", "영암", "무안", "함평", "영광", "장성", "완도", "진도", "신안", "경북", "포항", 
            "경주", "김천", "안동", "구미", "영주", "영천", "상주", "문경", "경산", "군위", "의성", 
            "청송", "영양", "영덕", "청도", "고령", "성주", "칠곡", "예천", "봉화", "울진", "울릉", 
            "경남", "창원", "진주", "통영", "사천", "김해", "밀양", "거제", "양산", "의령", "함안", 
            "창녕", "남해", "하동", "산청", "함양", "거창", "합천", "제주", "서귀포", "지자체", 
            "도청", "시청", "구청", "지역경제", "울산", "대구", "부산", "대전", "세종"
        ]
        if any(term in title for term in domestic_market_terms) or any(term in title for term in domestic_regions):
            if any(term in title for term in ["반도체", "hbm", "dram", "낸드", "삼성전자", "sk하이닉스", "삼성", "하이닉스"]):
                return "반도체"
            elif any(term in title for term in domestic_regions):
                return "정부정책"
            else:
                return "경제 일반"
    if sector == "원자재":
        raw_material_terms = [
            "구리", "철강", "알루미늄", "희토류", "유가", "석유", "가스", "에너지", "광물", 
            "리튬", "니켈", "우라늄", "펄프", "원두", "석탄", "곡물", "밀", "배터리 광물", "소재", "금속",
            "순금", "백금", "원자재", "원유", "천연가스", "아연", "납", "주석", "팔라듐", "대두", "옥수수"
        ]
        has_real_material = any(term in title for term in raw_material_terms)
        if "은" in title:
            if "은" in re.sub(r'은퇴|은닉|은빛|은근|은혜|은반|~은|은\s|은색', '', title):
                has_real_material = True
        if "금" in title:
            if "금" in re.sub(r'금리|금융|금지|금투세|모금|임금|송금|연금|황금|도금|합금|예금|출금|입금|세금|금물|금액|자금|금요일|대금|지금|요금|궁금|해금|소금', '', title):
                has_real_material = True
        if not has_real_material:
            if any(term in full_text for term in ["바이오", "제약", "신약", "치료제", "임상", "의료", "백신", "dna", "rna", "k-바이오"]):
                return "BIO / 의료AI"
            elif any(term in full_text for term in ["빅테크", "금리", "연준", "fed", "채권", "fomc", "국채"]):
                return "국제 - 미국"
            elif any(term in full_text for term in ["ai", "로봇", "인공지능", "gpt", "llm"]):
                return "AI / 로봇"
            else:
                return "경제 일반"
    return sector

def route_news_by_similarity(collected_news, threshold=None, skip_sectors=None):
    print("🔀 임베딩 유사도 기반 뉴스 라우팅 시작...")
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD
    if skip_sectors is None:
        skip_sectors = []
    routed_result = { sector: [] for sector in KEYWORD_EMBEDDED_DB.keys() }
    if not collected_news:
        return routed_result
    # 제목 + desc 앞 150자를 합쳐 임베딩 → 본문 맥락이 반영되어 섹터 분류 정확도 향상
    texts = [news["title"] + " " + news.get("desc", "")[:150] for news in collected_news]
    news_embeddings = embed_model.encode(texts, convert_to_tensor=True)
    routed_count = 0
    for idx, news in enumerate(collected_news):
        news_emb = news_embeddings[idx]
        best_sector = None
        best_keyword = None
        max_score = 0.0
        for sector, data in KEYWORD_EMBEDDED_DB.items():
            if sector in skip_sectors:
                continue
            if data["embeddings"] is None:
                continue
            scores = util.cos_sim(news_emb, data["embeddings"])[0]
            for kw_idx, score in enumerate(scores):
                if score > max_score:
                    max_score = score
                    best_sector = sector
                    best_keyword = data["keywords"][kw_idx]
        if max_score >= threshold:
            final_sector = check_and_adjust_sector(news, best_sector)
            # 앵커 키워드 검증: 제목에 섹터 대표어가 하나도 없으면 기타로 강제 이동
            if not validate_anchor_keyword(news["title"], final_sector):
                print(f"⚠️ [앵커 게이트] '{news['title'][:30]}' → 기타로 이동")
                final_sector = "기타"
            news["matched_keyword"] = best_keyword
            news["score"] = float(max_score)
            routed_result[final_sector].append(news)
            routed_count += 1
    print(f"🎯 유사도 필터링 완료: 전체 {len(collected_news)}건 중 {routed_count}건 매칭 성공 (임계치: {threshold:.2f}).")
    return routed_result

def deduplicate_routed_news(routed_news_data, dedup_threshold=0.70):
    print("🧹 섹터별 중복 및 유사 뉴스 제거 시작...")
    deduplicated_result = {}
    total_removed = 0
    for sector, news_list in routed_news_data.items():
        if not news_list:
            deduplicated_result[sector] = []
            continue
        if len(news_list) == 1:
            deduplicated_result[sector] = news_list
            continue
        titles = [news["title"] for news in news_list]
        embeddings = embed_model.encode(titles, convert_to_tensor=True)
        keep_indices = []
        removed_indices = set()
        for i in range(len(news_list)):
            if i in removed_indices:
                continue
            for j in range(i + 1, len(news_list)):
                if j in removed_indices:
                    continue
                sim = float(util.cos_sim(embeddings[i], embeddings[j])[0][0])
                if sim >= dedup_threshold:
                    if news_list[i]["score"] >= news_list[j]["score"]:
                        removed_indices.add(j)
                        print(f"🗑️ [{sector}] 중복 제거 (유사도 {sim:.2f}): [{news_list[j]['title']}] 제거")
                    else:
                        removed_indices.add(i)
                        print(f"🗑️ [{sector}] 중복 제거 (유사도 {sim:.2f}): [{news_list[i]['title']}] 제거")
                        break
            if i not in removed_indices:
                keep_indices.append(i)
        deduped_list = [news_list[idx] for idx in keep_indices]
        deduplicated_result[sector] = deduped_list
        total_removed += (len(news_list) - len(deduped_list))
    print(f"✅ 중복/유사 뉴스 제거 완료: 총 {total_removed}건의 기사 필터링됨.")
    return deduplicated_result

def generate_summary_local_fallback(routed_news_data, sectors):
    final_md = []
    for sector in sectors:
        if sector not in routed_news_data:
            continue
        news_list = routed_news_data[sector]
        final_md.append(f"### {sector}")
        if not news_list:
            final_md.append("--------")
        else:
            seen_titles = set()
            for news in news_list:
                title_clean = news['title'].strip()
                if title_clean in seen_titles:
                    continue
                seen_titles.add(title_clean)
                final_md.append(f"* [{news['title']}]({news['link']})")
                desc = news['desc'].strip()
                sentences = re.split(r'(?<=[.!?])\s+', desc)
                summary_desc = " ".join(sentences[:2]) if sentences else desc
                final_md.append(f"  {summary_desc}")
                final_md.append("")
        final_md.append("")
    return "\n".join(final_md)

def _generate_summary_for_sectors(sectors, routed_news_data):
    context_lines = []
    total_news_count = 0
    for sector in sectors:
        news_list = routed_news_data.get(sector, [])
        context_lines.append(f"[{sector}]")
        if not news_list:
            context_lines.append("데이터 없음")
        else:
            total_news_count += len(news_list)
            for idx, news in enumerate(news_list, 1):
                context_lines.append(f"{idx}. 제목: {news['title']}")
                context_lines.append(f"   링크: {news['link']}")
                context_lines.append(f"   내용: {news['desc']}")
                context_lines.append(f"   매칭키워드: {news['matched_keyword']} (유사도 {news['score']:.2f}) | {news['pub_time']}")
        context_lines.append("")
        
    if total_news_count == 0:
        empty_md = []
        for sector in sectors:
            empty_md.append(f"### {sector}")
            empty_md.append("--------")
            empty_md.append("")
        return "\n".join(empty_md)
        
    context_text = "\n".join(context_lines)
    prompt = f"""
당신은 한국 주식 시황을 정밀 요약하는 '수석 시황 에이전트'입니다.
제공된 뉴스 데이터를 최종 검토하여 지정된 섹터들에 대한 요약 보고서를 작성해 주세요.

[요청 사항]
1. 제공된 뉴스 목록 중 제목과 내용이 완전히 동일하거나 중복되는 기사는 1개만 남기고 삭제합니다. 단, 세부 수치나 대상 기업, 다른 관점을 다루는 기사는 최대한 살려서 리포트에 포함해 주세요.
2. 각 기사의 제목 자체를 클릭할 수 있도록 `[실제 기사 제목](기사 링크)` 마크다운 하이퍼링크 포맷으로 작성해 주세요. (예: `* [현대로템, 모로코서 수주](링크)` 형태로 만들고, `[[뉴스 제목](링크)] 실제 제목`처럼 '뉴스 제목'이라는 글자를 링크 텍스트로 쓰지 마세요.)
3. 각 뉴스 밑에는 1~2문장의 명확하고 핵심 수치(금액, 규모, 대상 등)가 포함된 요약 내용을 적어주세요.
4. 뉴스가 없거나 '데이터 없음'으로 표시된 섹션은 빈칸으로 두지 말고 반드시 해당 섹터 아래에 `--------` 로 표시해야 합니다.
5. 출력은 절대 부연설명이나 인사말 없이 마크다운 본문만 반환해야 합니다.
6. [오분류 조정 및 정제 규칙 (매우 중요)]
    최종 검토자로서 1차적으로 섹터 하위에 오분류된 기사를 발견 시 올바른 섹터로 반드시 이동시켜 작성하세요. (단, 이 파트의 대상 섹터 목록에 해당하는 경우에만 이동시킵니다.)
    - [국제 - 미국] 섹션: 미국 현지 지표(CPI, PCE), 대선 정치, 미 연준(Fed) 금리/통화정책 등 미국 매크로/빅테크 자체 소식만 다뤄야 합니다.
      * '코스피 1만 시대 가려면' 같은 국내 증시 뉴스나 한은 관련 한국 국내 뉴스는 절대로 여기에 두지 말고 [경제 일반]이나 [반도체](반도체 주도 내용이 주된 경우)로 이동하십시오.
      * '경기도 4차산업혁명센터', '천안아산 K-AI 시티', '안양시 지역경제 활성화' 등 국내 지자체(경기도, 천안, 아산, 춘천, 안양 등) 관련 정책 뉴스는 반드시 [정부정책] 섹터로 이동하십시오.
    - [원자재] 섹션: 금, 은, 구리, 철강, 알루미늄, 희토류, 유가(석유), 가스, 석탄, 곡물, 밀 등 실제 '물리적 원자재'와 관련된 기사만 다뤄야 합니다.
      * 빅테크 기업의 데이터센터 확장이나 국채 발행, 금리/채권 민감도 등의 소식은 [국제 - 미국] 또는 [경제 일반] 섹터로 이동하십시오.
      * 바이오 기술 개발, 신약 임상, 제약사 관련 뉴스는 원자재가 아니므로 반드시 [BIO / 의료AI] 섹터로 이동하십시오.
      * 인공지능(AI), 로봇 관련 뉴스는 [AI / 로봇] 섹터로 이동하십시오.

[대상 섹터 목록]
{chr(10).join(['- ' + s for s in sectors])}

[입력 데이터]
{context_text}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192
        }
    }
    max_retries = 3
    base_delay = 5
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                return content.strip()
        except Exception as e:
            print(f"⚠️ Gemini API 호출 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                return generate_summary_local_fallback(routed_news_data, sectors)

def generate_summary_with_gemini(routed_news_data):
    """라우팅된 뉴스 목록을 바탕으로 로컬에서 뉴스 요약(상위 2문장)을 직접 추출하여 다이제스트 보고서를 만듭니다. (Gemini API 미사용)"""
    SECTOR_ORDER = [
        "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
        "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
        "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
        "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
    ]
    
    md_lines = []
    # 발행 직전 크로스섹터 전역 중복 제거: 섹터를 넘어 동일 URL이 중복 노출되지 않도록 한 번만 초기화
    seen_links = set()
    
    for sector in SECTOR_ORDER:
        md_lines.append(f"- {sector}")
        news_list = routed_news_data.get(sector, [])
        if not news_list:
            md_lines.append("--------")
        else:
            for news in news_list:
                link = news.get("link", "")
                if link in seen_links:
                    continue
                seen_links.add(link)
                
                title = news.get("title", "").strip()
                title_escaped = title.replace("[", "\\[").replace("]", "\\]")
                md_lines.append(f"*   [{title_escaped}]({link})")
                
                # 뉴스 내용에서 상위 2문장 가져오기
                desc = news.get("desc", "").strip()
                sentences = re.split(r'(?<=[.!?])\s+', desc)
                top_two = [s.strip() for s in sentences[:2] if s.strip()]
                summary_desc = " ".join(top_two)
                
                if summary_desc:
                    md_lines.append(f"    {summary_desc}")
                else:
                    md_lines.append("    요약 내용 없음")
                md_lines.append("")
        md_lines.append("")
        
    return "\n".join(md_lines).strip()

def parse_time_arguments():
    # KST 기준 시간 획득
    kst_tz = timezone(timedelta(hours=9))
    now = datetime.now(kst_tz)
    
    if len(sys.argv) == 1:
        if now.weekday() == 6:
            start_time = (now - timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=17, minute=0, second=0, microsecond=0)
        elif now.weekday() == 0:
            start_time = (now - timedelta(days=3)).replace(hour=17, minute=0, second=0, microsecond=0)
            end_time = (now - timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        else:
            days_to_friday = (now.weekday() - 4) % 7
            friday = now - timedelta(days=days_to_friday)
            start_time = friday.replace(hour=17, minute=0, second=0, microsecond=0)
            end_time = (start_time + timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0)
        print(f"🌆 [주말 자동 KST 분석 모드] 수집 범위: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
        return start_time.replace(tzinfo=None), end_time.replace(tzinfo=None)
    if len(sys.argv) == 2:
        date_str = sys.argv[1]
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            start_time = (target_date - timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0)
            end_time = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
            print(f"📅 [주말 특정 일자 분석 모드] 기준일자: {date_str} (수집 범위: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')})")
            return start_time, end_time
        except ValueError:
            pass
    if len(sys.argv) == 5:
        try:
            start_str = f"{sys.argv[1]} {sys.argv[2]}:00"
            end_str = f"{sys.argv[3]} {sys.argv[4]}:00"
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            print(f"⏱️ [사용자 범위 지정 모드] 수집 범위: {start_str[:-3]} ~ {end_str[:-3]}")
            return start_time, end_time
        except ValueError:
            pass
    print("⚠️ 잘못된 인자 형식입니다. 아래와 같이 사용하세요:")
    print("  1) 실시간 자동 범위: python3 데일리뉴스(주말).py")
    print("  2) 특정 월요일 기준(이전 금~일): python3 데일리뉴스(주말).py 2026-06-22")
    print("  3) 세부 범위 지정:   python3 데일리뉴스(주말).py 2026-06-19 17:00 2026-06-21 17:00")
    sys.exit(1)

def main():
    start_time_perf = time.time()
    start_time, end_time = parse_time_arguments()
    
    if not os.path.exists(KEYWORDS_JSON_PATH):
        print(f"❌ 에러: {KEYWORDS_JSON_PATH} 파일이 존재하지 않습니다.")
        sys.exit(1)
        
    with open(KEYWORDS_JSON_PATH, "r", encoding="utf-8") as f:
        keyword_db = json.load(f)
        
    # 각 섹터의 구체적 키워드 리스트로부터 네이버 검색용 쿼리 추출 (172개 세부 키워드)
    search_queries = set()
    for sector, phrases in keyword_db.items():
        for phrase in phrases:
            sub_phrase = phrase.split(" 및 ")[0].split(" 또는 ")[0].split(" 혹은 ")[0]
            clean_phrase = re.sub(r'[\(\)\[\]\{\}]', ' ', sub_phrase)
            clean_phrase = re.sub(r'[,./··]', ' ', clean_phrase)
            words = [w.strip() for w in clean_phrase.split() if w.strip()]
            if words:
                query = " ".join(words[:4])
                search_queries.add(query)
                
    search_queries = sorted(list(search_queries))
    
    # 출력 파일명 설정 (일요일이 종점이면 다음날인 월요일 날짜로 파일명 생성)
    if end_time.weekday() == 6:
        target_file_date = end_time + timedelta(days=1)
    else:
        target_file_date = end_time
    OUTPUT_MD_PATH = f"reports/{target_file_date.strftime('%Y-%m-%d')}_주말.md"
    
    # 2단계 분할 수집 진행 (1000개 페이징 제한 우회 목적)
    mid_time = start_time + (end_time - start_time) / 2
    intervals = [
        (start_time, mid_time),
        (mid_time, end_time)
    ]
    
    all_collected_news = []
    seen_links = set()
    
    print(f"🔍 1차 수집 시작: 주말 분할 크롤링 (금 17:00 ~ 일 17:00, {len(search_queries)}개 세부 키워드, 각 수집 제한: 25개)...")
    for step, (s_t, e_t) in enumerate(intervals, 1):
        print(f"🔄 [{step}단계 수집] {s_t.strftime('%Y-%m-%d %H:%M')} ~ {e_t.strftime('%Y-%m-%d %H:%M')}")
        for idx, query in enumerate(search_queries):
            news_list = get_naver_news(query, s_t, e_t, max_news=15, require_digit=False)
            for news in news_list:
                if news["link"] not in seen_links:
                    seen_links.add(news["link"])
                    all_collected_news.append(news)
            
            if (idx + 1) % 20 == 0 or (idx + 1) == len(search_queries):
                print(f"   - [{idx + 1}/{len(search_queries)}] '{query}' 수집 완료 (현재 총 {len(all_collected_news)}건)")
            time.sleep(0.15)
            
    print(f"📥 네이버 중복 링크 제거 후 총 {len(all_collected_news)}건 수집 완료.")

    foreign_news = collect_foreign_rss(start_time, end_time)
    translated_foreign = []
    if foreign_news:
        translated_foreign = translate_foreign_titles_gemini(foreign_news)
        korea_terms = ["korea", "seoul", "한국", "대한민국", "서울", "s.korea", "s. korea"]
        filtered_foreign = []
        for news in translated_foreign:
            if news["link"] in seen_links:
                continue
            text_to_check = (news.get("title", "") + " " + news.get("title_original", "") + " " + news.get("desc", "")).lower()
            is_about_korea = any(term in text_to_check for term in korea_terms)
            if is_about_korea:
                print(f"🚫 해외 뉴스 중 한국 관련 기사 필터링 제외: {news['title']}")
                continue
            filtered_foreign.append(news)
        translated_foreign = filtered_foreign
        print(f"📰 해외 기사 번역 완료 (한국 제외): {len(translated_foreign)}건")

    if not all_collected_news and not translated_foreign:
        print("수집된 뉴스가 없습니다. 종료합니다.")
        return

    routed_domestic = route_news_by_similarity(all_collected_news, threshold=0.57, skip_sectors=["해외 이슈"])
    deduped_domestic = deduplicate_routed_news(routed_domestic, dedup_threshold=DEDUP_THRESHOLD)

    deduped_foreign = {}
    if translated_foreign:
        routed_foreign = route_news_by_similarity(translated_foreign, threshold=0.60)
        deduped_foreign = deduplicate_routed_news(routed_foreign, dedup_threshold=DEDUP_THRESHOLD)

    routed_data = {}
    all_sectors = set(list(deduped_domestic.keys()) + list(deduped_foreign.keys()))
    for sector in all_sectors:
        merged_list = deduped_domestic.get(sector, []) + deduped_foreign.get(sector, [])
        merged_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        routed_data[sector] = merged_list[:TOP_N_NEWS]

    final_report = generate_summary_with_gemini(routed_data)
    
    if final_report:
        os.makedirs(os.path.dirname(OUTPUT_MD_PATH), exist_ok=True)
        with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
            f.write(f"# 주말 뉴스\n")
            f.write(f"> 수집 시간: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(final_report)
            
        elapsed_time = time.time() - start_time_perf
        print(f"💾 최종 보고서가 '{OUTPUT_MD_PATH}'에 성공적으로 저장되었습니다. (소요시간: {elapsed_time:.1f}초)")
        
        # 텔레그램 알림 전송
        send_telegram_alert(final_report, target_file_date.strftime('%Y-%m-%d'), "주말")
    else:
        print("❌ 보고서 생성 실패.")

if __name__ == "__main__":
    main()

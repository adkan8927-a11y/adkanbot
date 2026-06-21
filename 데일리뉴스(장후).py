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
# 해외 RSS 피드 목록 (AI/빅테크, 매크로, 반도체, 지정학, 에너지)
# ==========================================
FOREIGN_RSS_FEEDS = [
    # Bloomberg
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.bloomberg.com/technology/news.rss",
    # Reuters
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    # CNBC
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    # Financial Times
    "https://www.ft.com/rss/home/us",
    # WSJ Markets
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    # Seeking Alpha (Market News)
    "https://seekingalpha.com/market_currents.xml",
]

# ==========================================
# 1. 필수 라이브러리 확인 및 자동 설치
# ==========================================
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    print("⚡ sentence-transformers 또는 torch 라이브러리가 존재하지 않아 자동 설치를 진행합니다...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "torch"])
        from sentence_transformers import SentenceTransformer, util
        import torch
        print("✅ 라이브러리 설치 및 불러오기 성공!")
    except Exception as install_err:
        print(f"❌ 라이브러리 자동 설치 실패: {install_err}")
        print("수동으로 'pip install sentence-transformers torch'를 진행해 주세요.")
        sys.exit(1)

# ==========================================
# 2. API 키 및 경로 설정
# ==========================================
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "pgpbMmGVrHyECNJtvIG1")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "AJjwBxBc7f")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6KJkRvIzeRwbeHGxOMik8zALM8AD3nZsXuse392Gle_cQ")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

KEYWORDS_JSON_PATH = "키워드3.json"
OUTPUT_MD_PATH = "데일리뉴스(장후).md"

SIMILARITY_THRESHOLD = 0.57  # 유사도 임계치
DEDUP_THRESHOLD = 0.82       # 중복 제거 코사인 유사도 임계치 (기존 0.70에서 완화하여 과도정제 방지)
TOP_N_NEWS = 5               # 섹터별 리포트에 노출할 최대 뉴스 건수 (유사도 상위)

# ==========================================
# 3. 임베딩 모델 및 키워드 DB 초기화
# ==========================================
print("🧠 로컬 임베딩 모델 로딩 중 (jhgan/ko-sroberta-multitask)...")
try:
    embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    print("✅ 임베딩 모델 로딩 완료.")
except Exception as e:
    print(f"❌ 임베딩 모델 로딩 실패: {e}")
    sys.exit(1)

def load_and_embed_keywords():
    """키워드2.json을 읽고 각 섹터별 키워드를 임베딩 벡터로 사전에 변환합니다."""
    if not os.path.exists(KEYWORDS_JSON_PATH):
        print(f"❌ 에러: {KEYWORDS_JSON_PATH} 파일이 존재하지 않습니다.")
        sys.exit(1)
        
    with open(KEYWORDS_JSON_PATH, "r", encoding="utf-8") as f:
        keyword_db = json.load(f)
        
    embedded_db = {}
    total_kws = 0
    print("💾 키워드 데이터베이스 벡터화 중...")
    
    for sector, keywords in keyword_db.items():
        if not keywords:
            embedded_db[sector] = {"keywords": [], "embeddings": None}
            continue
            
        embeddings = embed_model.encode(keywords, convert_to_tensor=True)
        embedded_db[sector] = {
            "keywords": keywords,
            "embeddings": embeddings
        }
        total_kws += len(keywords)
        
    print(f"✅ {len(embedded_db)}개 섹터, 총 {total_kws}개 키워드 임베딩 완료.")
    return embedded_db

KEYWORD_EMBEDDED_DB = load_and_embed_keywords()

def send_telegram_alert(summary_text, report_date, report_type="장후"):
    """생성된 요약본의 주요 헤드라인과 GitHub Pages 링크를 텔레그램으로 알림합니다."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없어서 알림 전송을 건너뜁니다.")
        return
        
    github_user = os.environ.get("GITHUB_ACTOR", "adkan")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "daily-news-crawler").split("/")[-1]
    
    if report_type == "장전":
        file_name = "데일리뉴스(장전)_결과.html"
    elif report_type == "장후":
        file_name = "데일리뉴스(장후).html"
    else:
        file_name = f"{report_date}.html"
        
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

# ==========================================
# 4. 해외 RSS 뉴스 수집 로직
# ==========================================
def collect_foreign_rss(start_time, end_time, max_per_feed=30):
    """해외 주요 RSS 피드에서 지정된 시간 범위의 기사를 수집합니다."""
    print(f"\n🌐 해외 RSS 수집 시작 ({len(FOREIGN_RSS_FEEDS)}개 피드)...")
    collected = []
    seen_links = set()

    # KST → UTC 변환 (RSS pubDate는 UTC 기준)
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


# ==========================================
# 4c. 영문 제목 → 한국어 일괄 번역 (Gemini 1회 호출)
# ==========================================
def translate_foreign_titles_gemini(news_list):
    """영문 RSS 기사 제목을 Gemini API로 한국어로 일괄 번역합니다."""
    if not news_list:
        return news_list

    print(f"🔤 영문 기사 제목 {len(news_list)}건 한국어 번역 중 (Gemini)...")

    titles_numbered = "\n".join([f"{i+1}. {n['title']}" for i, n in enumerate(news_list)])

    prompt = f"""다음 영문 뉴스 제목들을 한국 주식/경제 시황 맥락에 맞는 자연스러운 한국어로 번역하세요.
번역 규칙:
- 회사명·인명은 한국 통용 표기 사용 (NVIDIA→엔비디아, Fed→연방준비제도, Trump→트럼프 등)
- 번역문만 번호 순서대로 출력하고 설명·원문은 포함하지 마세요.

{titles_numbered}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "thinkingConfig": {
                "thinkingLevel": "MINIMAL"
            }
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
                
            # 번호 파싱: "1. 번역문" 형식 추출
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
                print(f"🔄 {delay}초 대기 후 재시도합니다...")
                time.sleep(delay)
            else:
                print("❌ 최대 재시도 횟수를 초과했습니다. 원문 영문 제목으로 라우팅 진행합니다.")

    # 원문 제목 보존 후 한국어 제목으로 교체
    if translated_titles:
        for i, news in enumerate(news_list):
            if i < len(translated_titles) and translated_titles[i]:
                news["title_original"] = news["title"]
                news["title"] = translated_titles[i]
    return news_list


def clean_html(text):
    """HTML 태그 및 특수 기호 정제"""
    return re.sub(r'<[^>]+>', '', text).replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

def get_naver_news(keyword, start_time, end_time, max_news=100, require_digit=False):
    """지정된 시작시간 ~ 종료시간 범위 동안 해당 키워드로 네이버 뉴스 검색"""
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
                
                # 수집 범위를 벗어난 더 과거 뉴스가 나오기 시작하면 완전 종료 (내림차순 정렬이므로)
                if pub_date < start_time:
                    reached_past_limit = True
                    break
                    
                # 지정 범위보다 미래 뉴스는 수집하지 않고 다음 기사로 넘어가 스킵
                if pub_date > end_time:
                    continue
                    
                link = item.get('link', '')
                if link in seen_links:
                    continue
                    
                title = clean_html(item.get('title', ''))
                
                # 수치(숫자) 필수 필터링 조건
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

def check_and_adjust_sector(news, sector):
    """1차 매핑된 섹터가 상식적인 규칙에 맞는지 검사하여 필요 시 알맞게 보정합니다."""
    title = news["title"].lower()
    desc = news["desc"].lower()
    full_text = title + " " + desc
    
    # 1. 국제 - 미국 섹션 예외 처리 (국내 지명/국내 증시 단어가 제목에 있을 시 국내 섹터로 강제 보정)
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
        
        has_market = any(term in title for term in domestic_market_terms)
        has_region = any(term in title for term in domestic_regions)
        
        if has_market or has_region:
            # 반도체 관련 키워드가 있으면 반도체로 유도
            semiconductor_terms = ["반도체", "hbm", "dram", "낸드", "삼성전자", "sk하이닉스", "삼성", "하이닉스"]
            if any(term in title for term in semiconductor_terms):
                return "반도체"
            elif has_region:
                return "정부정책"
            else:
                return "경제 일반"
                
    # 2. 원자재 섹션 예외 처리 (실제 광물/원자재 명칭이 제목에 전혀 언급되지 않았는데 매핑된 오탐 보정)
    if sector == "원자재":
        raw_material_terms = [
            "구리", "철강", "알루미늄", "희토류", "유가", "석유", "가스", "에너지", "광물", 
            "리튬", "니켈", "우라늄", "펄프", "원두", "석탄", "곡물", "밀", "배터리 광물", "소재", "금속",
            "순금", "백금", "원자재", "원유", "천연가스", "아연", "납", "주석", "팔라듐", "대두", "옥수수"
        ]
        
        has_real_material = any(term in title for term in raw_material_terms)
        
        # '은' 또는 '금' 한 글자 단어가 포함된 경우 정밀 체크
        if "은" in title:
            # '은퇴', '은닉', '은빛' 등 제외 후 체크
            clean_title_silver = re.sub(r'은퇴|은닉|은빛|은근|은혜|은반|~은|은\s|은색', '', title)
            if "은" in clean_title_silver:
                has_real_material = True
                
        if "금" in title:
            # 금리, 금융, 금지 등의 단어 오탐 제외
            clean_title = re.sub(r'금리|금융|금지|금투세|모금|임금|송금|연금|황금|도금|합금|예금|출금|입금|세금|금물|금액|자금|금요일|대금|지금|요금|궁금|해금|소금', '', title)
            if "금" in clean_title:
                has_real_material = True
                
        if not has_real_material:
            # 바이오 관련이면 BIO, 테크/금융금리면 미국/매크로, AI 관련이면 AI / 로봇으로 변경
            if any(term in full_text for term in ["바이오", "제약", "신약", "치료제", "임상", "의료", "백신", "dna", "rna", "k-바이오"]):
                return "BIO / 의료AI"
            elif any(term in full_text for term in ["빅테크", "금리", "연준", "fed", "채권", "fomc", "국채"]):
                return "국제 - 미국"
            elif any(term in full_text for term in ["ai", "로봇", "인공지능", "gpt", "llm"]):
                return "AI / 로봇"
            else:
                return "경제 일반"
                
    return sector

# ==========================================
# 5. 유사도 기반 뉴스 라우팅 (1차 파이썬 필터)
# ==========================================
def route_news_by_similarity(collected_news, threshold=None, skip_sectors=None):
    """수집된 뉴스들을 키워드2.json 기반 유사도 매칭으로 알맞은 섹터에 할당합니다."""
    print("🔀 임베딩 유사도 기반 뉴스 라우팅 시작...")
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD
    if skip_sectors is None:
        skip_sectors = []
    
    routed_result = { sector: [] for sector in KEYWORD_EMBEDDED_DB.keys() }
    
    if not collected_news:
        return routed_result
        
    titles = [news["title"] for news in collected_news]
    news_embeddings = embed_model.encode(titles, convert_to_tensor=True)
    
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
            news["matched_keyword"] = best_keyword
            news["score"] = float(max_score)
            routed_result[final_sector].append(news)
            routed_count += 1
            
    print(f"🎯 유사도 필터링 완료: 전체 {len(collected_news)}건 중 {routed_count}건 매칭 성공 (임계치: {threshold:.2f}).")
    return routed_result

def deduplicate_routed_news(routed_news_data, dedup_threshold=0.70):
    """각 섹션 내에서 제목의 임베딩 유사도가 높은 중복/유사 뉴스를 제거하여 하나만 남깁니다."""
    print("🧹 섹터별 중복 및 유사 뉴스 제거 시작...")
    deduplicated_result = {}
    total_removed = 0
    
    for sector, news_list in routed_news_data.items():
        if not news_list:
            deduplicated_result[sector] = []
            continue
            
        # 기사가 1개인 경우 비교 대상이 없으므로 그대로 유지
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
                    
                # 두 뉴스 제목 간 코사인 유사도 계산
                sim = float(util.cos_sim(embeddings[i], embeddings[j])[0][0])
                if sim >= dedup_threshold:
                    # 두 기사가 유사함 -> 매칭 스코어가 더 높은 것을 남기고 나머지는 제거 대상에 추가
                    if news_list[i]["score"] >= news_list[j]["score"]:
                        removed_indices.add(j)
                        print(f"🗑️ [{sector}] 중복 제거 (유사도 {sim:.2f}): [{news_list[j]['title']}] 제거 (스코어 {news_list[i]['score']:.2f} 유지)")
                    else:
                        removed_indices.add(i)
                        print(f"🗑️ [{sector}] 중복 제거 (유사도 {sim:.2f}): [{news_list[i]['title']}] 제거 (스코어 {news_list[j]['score']:.2f} 유지)")
                        # i가 제거되었으므로 i 루프는 중단하고 j를 검사할 수 있도록 함
                        break
            
            if i not in removed_indices:
                keep_indices.append(i)
                
        deduped_list = [news_list[idx] for idx in keep_indices]
        deduplicated_result[sector] = deduped_list
        total_removed += (len(news_list) - len(deduped_list))
        
    print(f"✅ 중복/유사 뉴스 제거 완료: 총 {total_removed}건의 기사 필터링됨.")
    return deduplicated_result


# ==========================================
# 6. 로컬 백업 요약 (2차 필터 실패 시 폴백)
# ==========================================
def generate_summary_local_fallback(routed_news_data):
    """Gemini API 호출 실패 시, 로컬에서 수집된 정보로 기본적인 마크다운 보고서를 조립합니다."""
    print("⚠️ API 제한으로 인해 로컬 백업 포맷터를 사용하여 보고서를 생성합니다.")
    
    # 6. [오분류 조정 및 정제 규칙 (매우 중요)]
    # 최종 검토자로서 1차적으로 섹터 하위에 오분류된 기사를 발견 시 올바른 섹터로 반드시 이동시켜 작성하세요.
    # - [국제 - 미국] 섹션: 미국 현지 지표(CPI, PCE), 대선 정치, 미 연준(Fed) 금리/통화정책 등 미국 매크로/빅테크 자체 소식만 다뤄야 합니다.
    #   * '코스피 1만 시대 가려면' 같은 국내 증시 뉴스나 한은 관련 한국 국내 뉴스는 절대로 여기에 두지 말고 [경제 일반]이나 [반도체](반도체 주도 내용이 주된 경우)로 이동하십시오.
    #   * '경기도 4차산업혁명센터', '천안아산 K-AI 시티', '안양시 지역경제 활성화' 등 국내 지자체(경기도, 천안, 아산, 춘천, 안양 등) 관련 정책 뉴스는 반드시 [정부정책] 섹터로 이동하십시오.
    # - [원자재] 섹션: 금, 은, 구리, 철강, 알루미늄, 희토류, 유가(석유), 가스, 석탄, 곡물, 밀 등 실제 '물리적 원자재'와 관련된 기사만 다뤄야 합니다.
    #   * 빅테크 기업의 데이터센터 확장이나 국채 발행, 금리/채권 민감도 등의 소식은 [국제 - 미국] 또는 [경제 일반] 섹터로 이동하십시오.
    #   * 바이오 기술 개발, 신약 임상, 제약사 관련 뉴스는 원자재가 아니므로 반드시 [BIO / 의료AI] 섹터로 이동하십시오.
    #   * 인공지능(AI), 로봇 관련 뉴스는 [AI / 로봇] 섹터로 이동하십시오.
    
    SECTOR_ORDER = [
        "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
        "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
        "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
        "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
    ]
    
    final_md = []
    for sector in SECTOR_ORDER:
        if sector not in routed_news_data:
            continue
        news_list = routed_news_data[sector]
        final_md.append(f"<{sector}>")
        if not news_list:
            final_md.append("--------")
        else:
            seen_titles = set()
            for news in news_list:
                title_clean = news['title'].strip()
                if title_clean in seen_titles:
                    continue
                seen_titles.add(title_clean)
                
                final_md.append(f"[{news['title']}]({news['link']})")
                desc = news['desc'].strip()
                sentences = re.split(r'(?<=[.!?])\s+', desc)
                summary_desc = " ".join(sentences[:2]) if sentences else desc
                final_md.append(summary_desc)
                final_md.append("")
        final_md.append("")
    return "\n".join(final_md)

# ==========================================
# 7. Gemini 에이전트 최종 요약 (2차 필터 및 마크다운 정리)
# ==========================================
def generate_summary_with_gemini(routed_news_data):
    """라우팅된 뉴스 목록을 바탕으로 Gemini API를 호출하여 최종 다이제스트 보고서를 만듭니다."""
    print("🧠 Gemini 에이전트 2차 최종 요약 및 보고서 작성 중...")
    
    SECTOR_ORDER = [
        "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
        "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
        "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
        "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
    ]

    context_lines = []
    total_news_count = 0
    for sector in SECTOR_ORDER:
        if sector not in routed_news_data:
            continue
        news_list = routed_news_data[sector]
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
        print("💡 매칭된 뉴스가 0건이므로 LLM API 호출을 건너뛰고 빈 템플릿을 생성합니다.")
        empty_md = []
        for sector in SECTOR_ORDER:
            empty_md.append(f"<{sector}>")
            empty_md.append("--------")
            empty_md.append("")
        return "\n".join(empty_md)
        
    context_text = "\n".join(context_lines)
    
    prompt = f"""
당신은 한국 주식 시황을 정밀 요약하는 '수석 시황 에이전트'입니다.
1차적으로 파이썬 알고리즘에 의해 섹터별로 분류된 뉴스 데이터를 최종 검토하여 고품질의 데일리 리포트를 생성해 주세요.

[요청 사항]
1. 제공된 뉴스 목록 중 제목과 내용이 완전히 동일하거나 중복되는 기사는 1개만 남기고 삭제합니다. 단, 세부 수치나 대상 기업, 다른 관점을 다루는 기사는 최대한 살려서 리포트에 포함해 주세요.
2. 각 기사의 제목 자체를 클릭할 수 있도록 `[실제 기사 제목](기사 링크)` 마크다운 하이퍼링크 포맷으로 작성해 주세요. (예: `* [현대로템, 모로코서 수주](링크)` 형태로 만들고, `[[뉴스 제목](링크)] 실제 제목`처럼 '뉴스 제목'이라는 글자를 링크 텍스트로 쓰지 마세요.)
3. 각 뉴스 밑에는 1~2문장의 명확하고 핵심 수치(금액, 규모, 대상 등)가 포함된 요약 내용을 적어주세요.
4. 뉴스가 없거나 '데이터 없음'으로 표시된 섹션은 빈칸으로 두지 말고 반드시 해당 섹터 아래에 `--------` 로 표시해야 합니다.
5. 출력은 절대 부연설명이나 인사말 없이 마크다운 본문만 반환해야 합니다.
6. [오분류 조정 및 정제 규칙 (매우 중요)]
    최종 검토자로서 1차적으로 섹터 하위에 오분류된 기사를 발견 시 올바른 섹터로 반드시 이동시켜 작성하세요.
    - [국제 - 미국] 섹션: 미국 현지 지표(CPI, PCE), 대선 정치, 미 연준(Fed) 금리/통화정책 등 미국 매크로/빅테크 자체 소식만 다뤄야 합니다.
      * '코스피 1만 시대 가려면' 같은 국내 증시 뉴스나 한은 관련 한국 국내 뉴스는 절대로 여기에 두지 말고 [경제 일반]이나 [반도체](반도체 주도 내용이 주된 경우)로 이동하십시오.
      * '경기도 4차산업혁명센터', '천안아산 K-AI 시티', '안양시 지역경제 활성화' 등 국내 지자체(경기도, 천안, 아산, 춘천, 안양 등) 관련 정책 뉴스는 반드시 [정부정책] 섹터로 이동하십시오.
    - [원자재] 섹션: 금, 은, 구리, 철강, 알루미늄, 희토류, 유가(석유), 가스, 석탄, 곡물, 밀 등 실제 '물리적 원자재'와 관련된 기사만 다뤄야 합니다.
      * 빅테크 기업의 데이터센터 확장이나 국채 발행, 금리/채권 민감도 등의 소식은 [국제 - 미국] 또는 [경제 일반] 섹터로 이동하십시오.
      * 바이오 기술 개발, 신약 임상, 제약사 관련 뉴스는 원자재가 아니므로 반드시 [BIO / 의료AI] 섹터로 이동하십시오.
      * 인공지능(AI), 로봇 관련 뉴스는 [AI / 로봇] 섹터로 이동하십시오.

[대상 섹터 목록]
- 경제 일반
- 부동산
- 미중패권전쟁
- 국제 - 미국
- 국제 - 유럽
- 국제 - 중국
- 국제 - 그외
- 원자재
- 정부정책
- 반도체
- 자동차
- 이차전지
- 전력 / 에너지
- AI / 로봇
- IT / 신기술
- BIO / 의료AI
- 조선 / 해운
- 우주 / 항공
- 코인 / STO
- IP / 엔터
- 건설 / 인프라
- 국방 / 방산
- 정치
- M&A / 주요 공시
- 해외 이슈 (Bloomberg, Reuters, FT 등 번역된 외신 — 이미 한국어 제목으로 변환됨)
- 기타

[입력 데이터]
{context_text}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
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
                return content
        except Exception as e:
            print(f"⚠️ Gemini API 호출 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"🔄 {delay}초 대기 후 재시도합니다...")
                time.sleep(delay)
            else:
                print("❌ 최대 재시도 횟수를 초과했습니다. 로컬 백업 포맷터로 전환합니다.")
                return generate_summary_local_fallback(routed_news_data)

# ==========================================
# 8. 메인 실행 제어 및 스마트 시간 설정
# ==========================================
def parse_time_arguments():
    """실행 인자를 파싱하여 수집 시작 시간과 종료 시간을 산출합니다."""
    now = datetime.now()
    
    # 1. 인자가 없는 경우: 장후 분석 기본 설정 (당일 08:00 ~ 17:00)
    if len(sys.argv) == 1:
        start_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour < 17:
            end_time = now
        else:
            end_time = now.replace(hour=17, minute=0, second=0, microsecond=0)
        print(f"🌆 [장후 분석 모드] 수집 범위: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
        return start_time, end_time

    # 2. 인자가 1개인 경우: YYYY-MM-DD 하루 기준 장후 수집 (당일 08:00 ~ 17:00)
    if len(sys.argv) == 2:
        date_str = sys.argv[1]
        try:
            start_time = datetime.strptime(f"{date_str} 08:00:00", "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(f"{date_str} 17:00:00", "%Y-%m-%d %H:%M:%S")
            print(f"📅 [특정 날짜 장후 모드] 수집 범위: {date_str} 08:00 ~ 17:00")
            return start_time, end_time
        except ValueError:
            pass

    # 3. 인자가 4개인 경우: YYYY-MM-DD HH:MM YYYY-MM-DD HH:MM 범위 지정 수집
    # 예: python3 데일리뉴스(장후).py 2026-06-19 08:00 2026-06-19 17:00
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

    # 형식이 맞지 않는 경우 사용 안내문 출력
    print("⚠️ 잘못된 인자 형식입니다. 아래와 같이 사용하세요:")
    print("  1) 실시간 자동 범위: python3 데일리뉴스(장후).py")
    print("  2) 특정 일자 장후 범위: python3 데일리뉴스(장후).py 2026-06-19")
    print("  3) 세부 범위 지정:   python3 데일리뉴스(장후).py 2026-06-19 08:00 2026-06-19 17:00")
    sys.exit(1)

def main():
    start_time_perf = time.time()
    
    # 시작 및 종료 시간 계산
    start_time, end_time = parse_time_arguments()
    
    # 키워드3.json 존재 여부 확인 (라우팅용)
    if not os.path.exists(KEYWORDS_JSON_PATH):
        print(f"❌ 에러: {KEYWORDS_JSON_PATH} 파일이 존재하지 않습니다.")
        sys.exit(1)
        
    # 5개 광범위 키워드로 설정 (특징주, 최초, 수주, 상승, 급등)
    search_queries = ["특징주", "최초", "수주", "상승", "급등"]
    
    all_collected_news = []
    seen_links = set()
    
    print(f"🔍 1차 수집 시작: 5개 핵심 키워드로 크롤링 (수집 제한: 100개)...")
    for idx, query in enumerate(search_queries):
        require_digit = (query in ["상승", "급등"])
        news_list = get_naver_news(query, start_time, end_time, max_news=100, require_digit=require_digit)
        for news in news_list:
            if news["link"] not in seen_links:
                seen_links.add(news["link"])
                all_collected_news.append(news)
        
        print(f"   [{idx + 1}/{len(search_queries)}] '{query}' 수집 완료 (현재 총 {len(all_collected_news)}건)")
            
        time.sleep(0.15)  # 과부하 방지용 0.15초 짧은 지연 (요청 간 텀 설정)
                
    print(f"📥 네이버 중복 링크 제거 후 총 {len(all_collected_news)}건 수집 완료.")

    # 1.5. 해외 RSS 수집 → Gemini 제목 번역 (통합하지 않고 별도 리스트 유지)
    foreign_news = collect_foreign_rss(start_time, end_time)
    translated_foreign = []
    if foreign_news:
        translated_foreign = translate_foreign_titles_gemini(foreign_news)
        # 중복 링크 제거 및 한국 관련 기사 제외
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

    # 2. 국내 뉴스 라우팅 및 중복 제거 (국내는 '해외 이슈'로 매핑되지 않도록 설정)
    routed_domestic = route_news_by_similarity(all_collected_news, threshold=0.57, skip_sectors=["해외 이슈"])
    deduped_domestic = deduplicate_routed_news(routed_domestic, dedup_threshold=DEDUP_THRESHOLD)

    # 2.5. 해외 뉴스 라우팅 및 중복 제거 (해외 뉴스는 0.60 임계치 적용)
    deduped_foreign = {}
    if translated_foreign:
        routed_foreign = route_news_by_similarity(translated_foreign, threshold=0.60)
        deduped_foreign = deduplicate_routed_news(routed_foreign, dedup_threshold=DEDUP_THRESHOLD)

    # 2.7. 국내 뉴스 + 해외 뉴스 섹션별 최종 병합 및 각 섹터별 유사도 상위 N건 선별
    routed_data = {}
    all_sectors = set(list(deduped_domestic.keys()) + list(deduped_foreign.keys()))
    for sector in all_sectors:
        merged_list = deduped_domestic.get(sector, []) + deduped_foreign.get(sector, [])
        # 유사도(score) 내림차순 정렬
        merged_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        # 상위 N건만 선정 (출력 글자수 한계 및 중요도 정제를 위함)
        routed_data[sector] = merged_list[:TOP_N_NEWS]

    # 3. 2차 최종 요약 리포트 작성
    final_report = generate_summary_with_gemini(routed_data)
    
    if final_report:
        # 4. 마크다운 파일로 저장
        with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
            f.write(f"# 데일리 시황 및 핵심 모멘텀 뉴스 정리\n")
            f.write(f"> 수집 범위: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"> 매칭 알고리즘: ko-sroberta-multitask (유사도 임계치 {SIMILARITY_THRESHOLD})\n\n")
            f.write(final_report)
            
        elapsed_time = time.time() - start_time_perf
        print(f"💾 최종 보고서가 '{OUTPUT_MD_PATH}'에 성공적으로 저장되었습니다. (소요시간: {elapsed_time:.1f}초)")
        
        # 텔레그램 알림 전송
        send_telegram_alert(final_report, end_time.strftime('%Y-%m-%d'), "장후")
    else:
        print("❌ 보고서 생성 실패.")

if __name__ == "__main__":
    main()

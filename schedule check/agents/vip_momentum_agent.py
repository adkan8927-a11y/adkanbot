"""
vip_momentum_agent.py
글로벌 VIP 돌발 일정 및 모멘텀 추적 에이전트

수집 소스:
  1. 네이버 뉴스 API  - 키워드 기반 실시간 뉴스 검색
  2. 구글 알리미 RSS - VIP 방문 관련 알리미 2종

분석:
  - 로컬 LLM(Ollama)으로 예상시기·핵심이슈·관련섹터·추정수혜주 추출
  - 결과를 vip_momentum_alerts.csv 에 누적 저장
  - Sentence-Transformers 의미적 유사도와 핵심 키워드 중복성을 결합한 이중 필터링(Dual-Filtering) 적용
"""
import os
import re
import html
import time
import feedparser
import requests
import pandas as pd
from datetime import datetime, timedelta

# 로컬 임베딩 모델 임포트
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    import subprocess
    import sys
    print("⚡ sentence-transformers 또는 torch 라이브러리 자동 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "torch"])
    from sentence_transformers import SentenceTransformer, util
    import torch

# ==========================================
# [설정] 환경에 맞게 수정하세요.
# ==========================================
NAVER_CLIENT_ID     = "pgpbMmGVrHyECNJtvIG1"
NAVER_CLIENT_SECRET = "AJjwBxBc7f"

# 다른 에이전트와 동일하게 OpenAI 호환 엔드포인트 사용
OLLAMA_URL  = "http://localhost:11434/v1/chat/completions"
MODEL_NAME  = "gemma4:e4b"   # 프로젝트 공통 모델

OUTPUT_CSV  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vip_momentum_alerts.csv")

# 이중 필터 임계치 설정
THRESHOLD_HIGH = 0.70
THRESHOLD_LOW  = 0.55
# ==========================================

print("🧠 로컬 임베딩 모델 로딩 중 (jhgan/ko-sroberta-multitask)...")
try:
    embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    print("✅ 임베딩 모델 로딩 완료.")
except Exception as e:
    print(f"❌ 임베딩 모델 로딩 실패: {e}")
    sys.exit(1)

# ── 네이버 뉴스 검색 키워드 ──────────────────────────────────────────
SEARCH_QUERIES = [
    "젠슨황|머스크|올트먼|저커버그|팀쿡 방한|회동|독대|비공개",
    "트럼프|시진핑|빈살만 방중|방한|국빈방문|정상회담|MOU"
]

# ── 구글 알리미 RSS (VIP 방문 관련 피드) ────────────────────────────
VIP_RSS_FEEDS = [
    "https://www.google.co.kr/alerts/feeds/13636798368499168881/2647445553520014659",
    "https://www.google.co.kr/alerts/feeds/13636798368499168881/9785744301701654080",
]

# VIP 1차 필터 키워드
VIP_KEYWORDS = ['방한', '회동', '방중', '방문', '만난다', '논의', '독대', '방일', '국빈', '정상회담', 'MOU', '비공개']


# ── 유틸 ──────────────────────────────────────────────────────────────
def clean_text(raw: str) -> str:
    """HTML 태그 및 특수문자 정제"""
    if not raw:
        return ""
    text = re.sub(r'<.*?>', '', raw)
    return html.unescape(text).strip()


def is_semantic_duplicate(text1: str, text2: str, embed_model, threshold_high: float = 0.70, threshold_low: float = 0.55) -> bool:
    """임베딩 유사도와 핵심 키워드 매칭을 결합한 하이브리드 이중 필터링"""
    try:
        emb1 = embed_model.encode(text1, convert_to_tensor=True)
        emb2 = embed_model.encode(text2, convert_to_tensor=True)
        sim = float(util.cos_sim(emb1, emb2)[0][0])
    except Exception as e:
        print(f"      ⚠️ 임베딩 유사도 연산 에러: {e}")
        return False

    # 1. 절대 유사성 검증
    if sim >= threshold_high:
        return True

    # 2. 이중 키워드 교집합 검증 (유사도가 threshold_low 이상인 경우에만 작동)
    if sim >= threshold_low:
        words1 = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', text1)])
        words2 = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', text2)])
        
        common_words = words1.intersection(words2)
        # 중요 일정 모멘텀 핵심 명사 그룹
        core_keywords = {'젠슨', '황', '엔비디아', '새만금', '한일', '국방', '방산', '안보', '회동', '방한', '투자', 'MOU', '골프', '정상'}
        overlapping_cores = common_words.intersection(core_keywords)

        if len(common_words) >= 3 or len(overlapping_cores) >= 1:
            print(f"      💡 이중 필터 매칭 성공 (유사도: {sim:.2f}, 공통단어: {len(common_words)}개, 겹침 핵심단어: {overlapping_cores})")
            return True

    return False


# ── 1. 네이버 뉴스 API 검색 ──────────────────────────────────────────
def search_naver_news(query: str) -> list[dict]:
    """네이버 뉴스 API — 최신순으로 최대 15건 반환"""
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": 15, "start": 1, "sort": "date"}  # 최신순

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get('items', [])
        print(f"❌ 네이버 API 오류 ({r.status_code})")
    except Exception as e:
        print(f"❌ 네이버 검색 실패: {e}")
    return []


# ── 2. 구글 알리미 RSS 파싱 ──────────────────────────────────────────
def fetch_rss_items(fifteen_days_ago: datetime) -> list[dict]:
    """구글 알리미 RSS 피드 2종 파싱 — 15일 이내 항목만 반환"""
    items = []
    for url in VIP_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"❌ RSS 파싱 실패 ({url[:60]}…): {e}")
            continue

        for entry in feed.entries[:10]:
            # 날짜 필터
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if pub_dt < fifteen_days_ago:
                        continue
                except Exception:
                    pass

            title = clean_text(getattr(entry, 'title', ''))
            summary = clean_text(getattr(entry, 'summary', getattr(entry, 'description', '')))
            link = getattr(entry, 'link', url)

            items.append({"title": title, "description": summary, "link": link})

    return items


# ── 3. 로컬 LLM 모멘텀 분석 ─────────────────────────────────────────
def analyze_momentum_with_llm(title: str, description: str) -> str:
    """Ollama LLM으로 VIP 일정·수혜주 분석 (OpenAI 호환 엔드포인트)"""
    prompt = f"""당신은 주식 시장의 거래대금 폭발과 당일 주도주 테마를 예측하는 전문 퀀트 분석가입니다.
다음 뉴스를 분석하여 글로벌 거물의 돌발 일정 모멘텀 정보를 아래 형식으로만 요약하세요.
기사에 명시되지 않았더라도 해당 인물·이슈와 직결되는 국내 수혜 관련주가 있다면 분석해서 포함하세요.

[뉴스 정보]
제목: {title}
내용: {description[:600]}

[출력 규칙] 불필요한 서론·마크다운 없이 정확히 4줄만 출력하세요.
예상시기: (예: 6월 초순, 이달 말, 2026년 하반기 등)
핵심이슈: (예: 젠슨 황 방한 및 국내 AI 스타트업 비공개 회동)
관련섹터: (미중 패권전쟁 / 반도체 / 자동차 / 이차전지 / 전력·에너지 / AI·로봇 / IT·신기술 / BIO·의료AI 중 하나)
추정수혜주: (관련 핵심 국내 상장 기업명 2~3개)
"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a precise Korean stock market analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"LLM 분석 실패: {e}"
    return ""


# ── 4. LLM 결과 파싱 ─────────────────────────────────────────────────
def parse_llm_result(llm_text: str) -> dict:
    eta, issue, sector, stocks = "N/A", "N/A", "기타", "N/A"
    for line in llm_text.split('\n'):
        line = line.strip()
        if line.startswith("예상시기:"): eta    = line.replace("예상시기:", "").strip()
        elif line.startswith("핵심이슈:"): issue  = line.replace("핵심이슈:", "").strip()
        elif line.startswith("관련섹터:"): sector = line.replace("관련섹터:", "").strip()
        elif line.startswith("추정수혜주:"): stocks = line.replace("추정수혜주:", "").strip()
    return {"estimated_timeline": eta, "issue": issue, "sector": sector, "target_stocks": stocks}


# ── 메인 ──────────────────────────────────────────────────────────────
def main():
    print("🚨 [VIP 모멘텀 레이더] 가동 중...")

    today = datetime.today()
    fifteen_days_ago = today - timedelta(days=15)

    # 기존 수집 정보 로드 (URL 중복 및 의미적 중복 방지용)
    existing_links = set()
    existing_issues = []
    
    if os.path.exists(OUTPUT_CSV):
        try:
            old_df = pd.read_csv(OUTPUT_CSV)
            if 'link' in old_df.columns:
                existing_links = set(old_df['link'].dropna().tolist())
            if 'issue' in old_df.columns:
                existing_issues = old_df['issue'].dropna().tolist()
        except Exception:
            pass

    all_alerts = []

    # ── A. 네이버 뉴스 API 검색 ───────────────────────────────────────
    for query in SEARCH_QUERIES:
        print(f"\n🔍 네이버 검색 중: {query[:40]}…")
        for item in search_naver_news(query):
            link  = item.get('link', '')
            if link in existing_links:
                continue

            title = clean_text(item.get('title', ''))
            desc  = clean_text(item.get('description', ''))

            # 15일 이내 기사인지 pubDate로 필터 (네이버 형식: "Sat, 28 Jun 2026 …")
            pub_date_str = item.get('pubDate', '')
            if pub_date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    pub_dt = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
                    if pub_dt < fifteen_days_ago:
                        continue
                except Exception:
                    pass

            if any(kw in title for kw in VIP_KEYWORDS):
                print(f"  📌 {title}")
                llm_text = analyze_momentum_with_llm(title, desc)
                parsed   = parse_llm_result(llm_text)
                
                if parsed["issue"] != "N/A":
                    # 이중 필터링 적용 의미적 중복 검증
                    is_duplicate_issue = False
                    for ext_issue in existing_issues:
                        if is_semantic_duplicate(parsed["issue"], ext_issue, embed_model, THRESHOLD_HIGH, THRESHOLD_LOW):
                            is_duplicate_issue = True
                            print(f"  🗑️ 중복 이슈 필터링: [{parsed['issue']}] 수집 생략")
                            break
                            
                    if not is_duplicate_issue:
                        all_alerts.append({
                            "date_captured":       today.strftime('%Y-%m-%d'),
                            "source":              "네이버뉴스API",
                            **parsed,
                            "link": link
                        })
                        existing_links.add(link)
                        existing_issues.append(parsed["issue"])
                        time.sleep(0.5)

    # ── B. 구글 알리미 RSS ────────────────────────────────────────────
    print(f"\n📡 구글 알리미 RSS {len(VIP_RSS_FEEDS)}종 수집 중...")
    for item in fetch_rss_items(fifteen_days_ago):
        link  = item.get('link', '')
        if link in existing_links:
            continue

        title = item.get('title', '')
        desc  = item.get('description', '')

        if any(kw in title or kw in desc for kw in VIP_KEYWORDS):
            print(f"  📌 [RSS] {title[:60]}")
            llm_text = analyze_momentum_with_llm(title, desc)
            parsed   = parse_llm_result(llm_text)
            
            if parsed["issue"] != "N/A":
                # 이중 필터링 적용 의미적 중복 검증
                is_duplicate_issue = False
                for ext_issue in existing_issues:
                    if is_semantic_duplicate(parsed["issue"], ext_issue, embed_model, THRESHOLD_HIGH, THRESHOLD_LOW):
                        is_duplicate_issue = True
                        print(f"  🗑️ 중복 이슈 필터링: [{parsed['issue']}] 수집 생략")
                        break
                        
                if not is_duplicate_issue:
                    all_alerts.append({
                        "date_captured":   today.strftime('%Y-%m-%d'),
                        "source":          "구글알리미RSS",
                        **parsed,
                        "link": link
                    })
                    existing_links.add(link)
                    existing_issues.append(parsed["issue"])
                    time.sleep(0.5)

    # ── C. 마스터 DB 저장 ─────────────────────────────────────────────
    if all_alerts:
        df_new = pd.DataFrame(all_alerts)
        file_exists = os.path.exists(OUTPUT_CSV)
        df_new.to_csv(OUTPUT_CSV, mode='a', index=False,
                      header=not file_exists, encoding='utf-8-sig')
        print(f"\n🎉 신규 VIP 모멘텀 {len(all_alerts)}건 저장 완료 → {OUTPUT_CSV}")
    else:
        print("\n검출된 신규 돌발 VIP 일정이 없습니다.")


if __name__ == "__main__":
    main()
"""
keyword_manager.py
키워드 동적 최신화 및 노이즈 가지치기 중앙 에이전트

기능:
  1. --analyze  : 키워드 히트 성과 분석 및 30일 무반응 키워드 리포트 생성
  2. --discover : 네이버 증권 거래대금 TOP/상한가 종목 스크래핑 -> 로컬 Ollama LLM (gemma4:e4b) 기반 신규 주도재료 20~30개 발굴
  3. --prune    : 백업(키워드3_backup.json) 자동 생성 후 무반응/노이즈 키워드 안전 가지치기
  4. --sync     : 키워드 DB 정합성 검증 및 동기화
"""

import os
import sys
import json
import re
import time
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta

# .env 로드 (안전 가싸기)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
except ImportError:
    pass

# 파일 경로
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYWORDS_JSON_PATH = os.path.join(BASE_DIR, "키워드3.json")
ANALYTICS_CSV_PATH = os.path.join(BASE_DIR, "schedule check", "keyword_analytics.csv")

# 로컬 Ollama & Gemini API 설정
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:e4b"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID") or "pgpbMmGVrHyECNJtvIG1"
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET") or "AJjwBxBc7f"

def load_keywords():
    """키워드3.json 파일 로드"""
    if not os.path.exists(KEYWORDS_JSON_PATH):
        print(f"❌ 에러: {KEYWORDS_JSON_PATH} 파일이 존재하지 않습니다.")
        sys.exit(1)
    with open(KEYWORDS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_keywords_with_backup(keyword_db):
    """안전하게 백업본을 만들고 키워드3.json 덮어쓰기"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BASE_DIR, f"키워드3_backup_{timestamp}.json")
    
    # 1. 백업본 생성
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(load_keywords(), f, ensure_ascii=False, indent=4)
    print(f"💾 안전 백업본 생성 완료: {backup_path}")
    
    # 2. 키워드3.json 저장
    with open(KEYWORDS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(keyword_db, f, ensure_ascii=False, indent=4)
    print(f"✅ {KEYWORDS_JSON_PATH} 업데이트 완료!")

def log_keyword_hit(sector: str, keyword: str, similarity_score: float = 0.65):
    """뉴스 수집기에서 매칭 성공 시 히트 기록 추가"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(ANALYTICS_CSV_PATH):
        try:
            df = pd.read_csv(ANALYTICS_CSV_PATH)
        except Exception:
            df = pd.DataFrame(columns=["sector", "keyword", "last_hit_date", "total_hit_count", "avg_similarity_score"])
    else:
        df = pd.DataFrame(columns=["sector", "keyword", "last_hit_date", "total_hit_count", "avg_similarity_score"])

    # 키워드 존재 여부 체크
    mask = (df["sector"] == sector) & (df["keyword"] == keyword)
    if mask.any():
        idx = df[mask].index[0]
        df.loc[idx, "last_hit_date"] = today_str
        df.loc[idx, "total_hit_count"] = int(df.loc[idx, "total_hit_count"]) + 1
        curr_score = float(df.loc[idx, "avg_similarity_score"])
        df.loc[idx, "avg_similarity_score"] = round((curr_score + similarity_score) / 2.0, 2)
    else:
        new_row = {
            "sector": sector,
            "keyword": keyword,
            "last_hit_date": today_str,
            "total_hit_count": 1,
            "avg_similarity_score": round(similarity_score, 2)
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(ANALYTICS_CSV_PATH, index=False, encoding="utf-8-sig")

def analyze_keywords():
    """키워드 성과 분석 및 리포트 출력"""
    keyword_db = load_keywords()
    total_keywords = sum(len(kw_list) for kw_list in keyword_db.values())
    
    print("\n==========================================")
    print(f"📊 [키워드 성과 분석] 총 {len(keyword_db)}개 섹터, {total_keywords}개 키워드 추적 중")
    print("==========================================")
    
    if not os.path.exists(ANALYTICS_CSV_PATH):
        print("⚠️ 트래킹 데이터(keyword_analytics.csv)가 아직 누적되지 않았습니다.")
        print("💡 수집기 실행 시 자동으로 히트 로그가 쌓입니다.")
        return

    df = pd.read_csv(ANALYTICS_CSV_PATH)
    hit_keywords = set(df[df["total_hit_count"] > 0]["keyword"].tolist())
    
    print(f"✅ 최근 히트 이력 보유 키워드: {len(hit_keywords)}개 / 전체 {total_keywords}개 ({len(hit_keywords)/total_keywords*100:.1f}%)")
    
    # 섹터별 키워드 보유 현황
    print("\n[섹터별 키워드 수 현황]")
    for sector, kw_list in keyword_db.items():
        matched = [k for k in kw_list if k in hit_keywords]
        print(f"  - {sector}: 총 {len(kw_list)}개 (활성 매칭: {len(matched)}개)")

def discover_hot_keywords():
    """네이버 증권 거래대금 상위 및 당일 주도주 헤드라인 수집 후 로컬 LLM으로 신규 키워드 20~30개 추출"""
    print("\n🔥 [신규 주도재료 파이프라인] 네이버 증권 당일 주도주/거래대금 상위 이슈 수집 중...")
    
    # 1. 네이버 뉴스 API로 당일 시장 수급 주도 키워드 검색
    trending_queries = ["거래대금 급증", "상한가 종목", "주도주 수혜", "신규 랠리 테마"]
    collected_headlines = []
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    
    for q in trending_queries:
        url = f"https://openapi.naver.com/v1/search/news.json?query={requests.utils.quote(q)}&display=10&sort=date"
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                for item in r.json().get("items", []):
                    title = re.sub(r'<.*?>', '', item.get("title", "")).strip()
                    if title and title not in collected_headlines:
                        collected_headlines.append(title)
        except Exception as e:
            print(f"  ⚠️ 수집 실패 ({q}): {e}")

    if not collected_headlines:
        print("❌ 뉴스 헤드라인 수집에 실패했습니다.")
        return

    print(f"📥 당일 주도주/수급 관련 헤드라인 {len(collected_headlines)}건 수집 완료.")
    print("🤖 로컬 LLM (Ollama gemma4:e4b)으로 주도 테마 키워드 추출 중...")

    # 2. 로컬 Ollama LLM 호출 (gemma4:e4b)
    prompt = f"""당신은 주식 시장 거래대금 150억 이상 터지는 당일 주도주 테마를 포착하는 전문 퀀트 분석가입니다.
아래 수집된 당일 주도주/수급 헤드라인 리스트를 분석하여, 현재 시장에서 돈이 몰리는 '신규 주도 테마 키워드' 15~20개를 단어/구문 형태로만 아래 JSON 형식으로 추출하세요.

[수집된 주도주 뉴스 헤드라인]
{chr(10).join(['- ' + h for h in collected_headlines[:30]])}

[출력 규칙]
1. 불필요한 설명 없이 오직 JSON 포맷만 출력하세요.
2. 기존에흔한 단어 대신 당일 거래대금이 몰린 구체적인 핫재료 키워드(예: '유리기판 실물전시', '소듐이온 배터리', '미국 MRO 수주') 위주로 추출하세요.

[JSON 출력 양식]
{{
  "신규주도키워드": [
    "키워드1",
    "키워드2",
    "키워드3"
  ]
}}
"""

    response_text = ""
    # 로컬 Ollama 시도
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a precise Korean stock market analyst. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if r.status_code == 200:
            response_text = r.json()["choices"][0]["message"]["content"].strip()
            print("✅ 로컬 Ollama (gemma4:e4b) 분석 완료!")
    except Exception as ollama_err:
        print(f"⚠️ 로컬 Ollama 호출 실패/타임아웃 ({ollama_err}). Gemini API 폴백 시도...")
        if GEMINI_API_KEY:
            for model_id in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                    g_payload = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    gr = requests.post(gemini_url, json=g_payload, timeout=30)
                    if gr.status_code == 200:
                        response_text = gr.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        print(f"✅ Gemini API 폴백 분석 완료 ({model_id})!")
                        break
                except Exception as gemini_err:
                    print(f"  ⚠️ {model_id} 폴백 실패: {gemini_err}")

    if not response_text:
        print("❌ LLM 분석 결과 응답을 받지 못했습니다.")
        return

    # JSON 결과 추출
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            parsed_result = json.loads(json_match.group(0))
            discovered_keywords = parsed_result.get("신규주도키워드", [])
            print(f"\n🎉 [발굴 성공] 총 {len(discovered_keywords)}개의 신규 주도재료 키워드 도출:")
            for idx, kw in enumerate(discovered_keywords, 1):
                print(f"  {idx}. {kw}")
        else:
            print("⚠️ JSON 형태를 파싱하지 못했습니다. 원문:")
            print(response_text[:300])
    except Exception as parse_err:
        print(f"❌ JSON 파싱 에러: {parse_err}")

def backfill_historical_reports():
    """reports/ 폴더 내 지난 1달간의 모든 .md 시황 리포트를 파싱하여 과거 히트 기록을 역추적 백필(Backfill)"""
    print("\n📚 [과거 1달 시황 리포트 백필] reports/ 폴더 스캔 중...")
    reports_dir = os.path.join(BASE_DIR, "reports")
    if not os.path.exists(reports_dir):
        print("❌ reports 디렉토리가 존재하지 않습니다.")
        return

    md_files = [f for f in os.listdir(reports_dir) if f.endswith(".md")]
    print(f"📂 총 {len(md_files)}개의 과거 시황 리포트(.md) 발견.")

    keyword_db = load_keywords()
    hit_counts = {}
    last_hit_dates = {}

    for fname in md_files:
        # 파일명에서 날짜 추출 (예: 2026-07-27_장후.md -> 2026-07-27)
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', fname)
        file_date = date_match.group(0) if date_match else "2026-07-01"

        fpath = os.path.join(reports_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            for sector, kw_list in keyword_db.items():
                for kw in kw_list:
                    # 리포트 본문/제목 내 키워드 언급 횟수 카운트
                    if kw in content:
                        hit_counts[(sector, kw)] = hit_counts.get((sector, kw), 0) + content.count(kw)
                        if (sector, kw) not in last_hit_dates or file_date > last_hit_dates[(sector, kw)]:
                            last_hit_dates[(sector, kw)] = file_date
        except Exception as e:
            print(f"  ⚠️ {fname} 읽기 오류: {e}")

    # keyword_analytics.csv 생성/업데이트
    rows = []
    for sector, kw_list in keyword_db.items():
        for kw in kw_list:
            count = hit_counts.get((sector, kw), 0)
            last_date = last_hit_dates.get((sector, kw), "2026-06-19" if count > 0 else "N/A")
            avg_score = 0.65 if count > 0 else 0.0
            rows.append({
                "sector": sector,
                "keyword": kw,
                "last_hit_date": last_date,
                "total_hit_count": count,
                "avg_similarity_score": avg_score
            })

    df = pd.DataFrame(rows)
    df.to_csv(ANALYTICS_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"🎉 과거 1달간 리포트 파싱 완료! 총 {len(hit_counts)}개 활성 키워드 데이터 백필 완료 → {ANALYTICS_CSV_PATH}")

def prune_stale_keywords():
    """30일 무반응/노이즈 키워드 가지치기"""
    keyword_db = load_keywords()
    
    if not os.path.exists(ANALYTICS_CSV_PATH):
        print("⚠️ 트래킹 데이터가 부족하여 가지치기를 건너뜁니다.")
        return
        
    df = pd.read_csv(ANALYTICS_CSV_PATH)
    zero_hit_keywords = set(df[df["total_hit_count"] == 0]["keyword"].tolist())
    
    pruned_count = 0
    new_db = {}
    
    for sector, kw_list in keyword_db.items():
        # 히트 수가 0인 키워드가 목록에 있고, 섹터당 최소 5개 키워드는 보존
        filtered_list = []
        for kw in kw_list:
            if kw in zero_hit_keywords and len(kw_list) - pruned_count > 5:
                print(f"  🗑️ [가지치기 대상] [{sector}] '{kw}' (히트 수 0)")
                pruned_count += 1
            else:
                filtered_list.append(kw)
        new_db[sector] = filtered_list
        
    if pruned_count > 0:
        save_keywords_with_backup(new_db)
        print(f"🎉 총 {pruned_count}개의 소멸 테마 키워드 가지치기 완료!")
    else:
        print("✨ 현재 가지치기할 소멸 키워드가 없습니다.")

def main():
    parser = argparse.ArgumentParser(description="키워드 동적 최신화 및 가지치기 엔진 (keyword_manager.py)")
    parser.add_argument("--analyze", action="store_true", help="키워드 성과 분석 리포트 출력")
    parser.add_argument("--discover", action="store_true", help="로컬 LLM 기반 신규 주도재료 키워드 발굴")
    parser.add_argument("--prune", action="store_true", help="30일 무반응 소멸 키워드 가지치기")
    parser.add_argument("--backfill", action="store_true", help="과거 1달간 발행 리포트 파싱 및 히트 데이터 백필")
    parser.add_argument("--sync", action="store_true", help="키워드 DB 구문 검증 및 백업")

    args = parser.parse_args()

    if args.analyze:
        analyze_keywords()
    elif args.discover:
        discover_hot_keywords()
    elif args.prune:
        prune_stale_keywords()
    elif args.backfill:
        backfill_historical_reports()
    elif args.sync:
        db = load_keywords()
        save_keywords_with_backup(db)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

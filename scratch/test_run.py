import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
import urllib.request
import requests
from sentence_transformers import SentenceTransformer, util

# 데일리뉴스(장후).py가 위치한 경로 로딩
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util

spec = importlib.util.spec_from_file_location("base_scraper", "데일리뉴스(장후).py")
base_scraper = importlib.util.module_from_spec(spec)
sys.modules["base_scraper"] = base_scraper
spec.loader.exec_module(base_scraper)

embed_model = base_scraper.embed_model
KEYWORD_EMBEDDED_DB = base_scraper.KEYWORD_EMBEDDED_DB

def run_experiment(dedup_threshold, output_file, experiment_name):
    print(f"\n🧪 [{experiment_name}] 실험 시작 (중복 판정 임계치: {dedup_threshold})")
    
    # 2026-06-26 하루 분량 데이터 (동일 시점의 수집 데이터 통제)
    start_time = datetime(2026, 6, 26, 8, 0)
    end_time = datetime(2026, 6, 26, 17, 0)
    
    # 캐시 파일 사용 (API Quota 절약)
    cache_path = "scratch/news_cache.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            collected_news = json.load(f)
        print(f"   📦 캐시에서 뉴스 로드 완료 ({len(collected_news)}건)")
    else:
        print("   🌐 뉴스 데이터 최초 수집 중...")
        with open("키워드3.json", "r", encoding="utf-8") as f:
            keyword_db = json.load(f)
            
        collected_news = []
        seen_links = set()
        for sector, keywords in keyword_db.items():
            for kw in keywords[:3]:  # 빠른 수집을 위한 핵심 키워드 검색
                news_items = base_scraper.get_naver_news(kw, start_time, end_time, max_news=30)
                for item in news_items:
                    if item["link"] not in seen_links:
                        seen_links.add(item["link"])
                        collected_news.append(item)
                        
        os.makedirs("scratch", exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(collected_news, f, ensure_ascii=False, indent=4)
        print(f"   📦 뉴스 수집 및 로컬 캐싱 완료 ({len(collected_news)}건)")

    # 1. 1차 라우팅 및 1차 기본 중복 제거 (0.82)
    routed_data = base_scraper.route_news_by_similarity(collected_news)
    
    # 2. 2차 섹터 정합성 검증 (0.50 컷)
    validated_news_data = { sector: [] for sector in routed_data.keys() }
    TOP_N_NEWS = 7  # 노출할 최대 기사 개수
    
    for sector, news_list in routed_data.items():
        if not news_list or sector == "기타":
            validated_news_data[sector] = news_list
            continue
            
        sector_data = KEYWORD_EMBEDDED_DB.get(sector)
        if sector_data is None or sector_data["embeddings"] is None:
            passed_news = news_list
        else:
            texts_to_verify = [n["title"] + " " + n.get("desc", "") for n in news_list]
            news_embeddings = embed_model.encode(texts_to_verify, convert_to_tensor=True)
            
            passed_news = []
            for idx, news in enumerate(news_list):
                news_emb = news_embeddings[idx]
                scores = util.cos_sim(news_emb, sector_data["embeddings"])[0]
                max_score = float(max(scores))
                if max_score >= 0.50:
                    passed_news.append(news)
                    
        # 3. 실험 핵심: 중복 검사 임계값(dedup_threshold)을 이용한 7개 채우기 무한 루프 스캐닝
        final_list = []
        for news in passed_news:
            if len(final_list) >= TOP_N_NEWS:
                break
            
            is_dupe = False
            if final_list:
                titles = [fn["title"] for fn in final_list] + [news["title"]]
                embeddings = embed_model.encode(titles, convert_to_tensor=True)
                sims = util.cos_sim(embeddings[-1], embeddings[:-1])[0]
                # 각 실험 차수별 임계치 대조
                if any(float(sim) >= dedup_threshold for sim in sims):
                    is_dupe = True
            
            if not is_dupe:
                final_list.append(news)
                
        validated_news_data[sector] = final_list

    # 마크다운 최종 보고서 조립
    md_content = base_scraper.generate_summary_local_fallback(validated_news_data, list(validated_news_data.keys()))
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"   💾 {output_file} 결과 리포트 저장 성공!\n")

if __name__ == "__main__":
    # 3차 (임계치 0.82) - 가장 널널하게 유사도 체크
    run_experiment(0.82, "3차.md", "3차 정합성 실험 (널널한 필터)")
    # 5차 (임계치 0.70) - 보편적인 중복 판정
    run_experiment(0.70, "5차.md", "5차 정합성 실험 (보통 필터)")
    # 7차 (임계치 0.60) - 아주 타이트하게 중복 판정
    run_experiment(0.60, "7차.md", "7차 정합성 실험 (매우 타이트한 필터)")

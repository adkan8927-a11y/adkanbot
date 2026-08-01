import os
import sys
import glob
import re
import time
import importlib.util
from datetime import datetime

print("🚀 7월 31일 뉴스 수집 및 26개 섹터 + Gemini AI 하이브리드 리포트 생성 시작...")

def import_script(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

Janghu = import_script("Janghu", "데일리뉴스(장후).py")
Jangjeon = import_script("Jangjeon", "데일리뉴스(장전).py")

MD_JANGHU_MODIFIED = "reports/2026-07-31_장후_수정.md"
MD_JANGJEON_MODIFIED = "reports/2026-07-31_장전_수정.md"

def collect_news_for_module(mod, start_time, end_time):
    search_queries = []
    for sector, data in mod.KEYWORD_EMBEDDED_DB.items():
        for kw in data["keywords"]:
            search_queries.append(kw)
            
    all_collected_news = []
    seen_links = set()
    
    print(f"🔍 네이버 뉴스 검색 시작 ({len(search_queries)}개 키워드)...")
    for idx, query in enumerate(search_queries):
        news_list = mod.get_naver_news(query, start_time, end_time, max_news=10)
        for news in news_list:
            if news["link"] not in seen_links:
                seen_links.add(news["link"])
                all_collected_news.append(news)
        time.sleep(0.05)
        
    print(f"📥 수집 완료: {len(all_collected_news)}건")
    
    foreign_news = mod.collect_foreign_rss(start_time, end_time)
    translated_foreign = []
    if foreign_news:
        translated_foreign = mod.translate_foreign_titles_gemini(foreign_news)
        korea_terms = ["korea", "seoul", "한국", "대한민국", "서울", "s.korea", "s. korea"]
        filtered_foreign = []
        for news in translated_foreign:
            if news["link"] in seen_links:
                continue
            text_to_check = (news.get("title", "") + " " + news.get("title_original", "") + " " + news.get("desc", "")).lower()
            if any(term in text_to_check for term in korea_terms):
                continue
            filtered_foreign.append(news)
        translated_foreign = filtered_foreign
        
    return all_collected_news, translated_foreign

SECTOR_ORDER = [
    "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
    "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
    "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
    "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
]

# 1. 7/31 장후 수정 리포트 생성
print("\n--------------------------------------------------")
print("📥 [1/2] 7월 31일 장후 뉴스 수집 & 하이브리드 라우팅 진행 중...")
print("--------------------------------------------------")

start_time_jh = datetime(2026, 7, 31, 0, 0, 0)
end_time_jh = datetime(2026, 7, 31, 23, 59, 59)

raw_news_jh, foreign_jh = collect_news_for_module(Janghu, start_time_jh, end_time_jh)

routed_domestic_jh = Janghu.route_news_by_similarity(raw_news_jh, threshold=0.59, skip_sectors=["해외 이슈"])
routed_foreign_jh = {}
if foreign_jh:
    routed_foreign_jh = Janghu.route_news_by_similarity(foreign_jh, threshold=0.60)

routed_data_jh = {}
global_links_jh = set()

for sector in SECTOR_ORDER:
    merged_list = routed_domestic_jh.get(sector, []) + routed_foreign_jh.get(sector, [])
    merged_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    selected_news = []
    for news in merged_list:
        link = news.get("link", "")
        if link in global_links_jh:
            continue
            
        is_duplicate = False
        if selected_news:
            titles = [n["title"] for n in selected_news] + [news["title"]]
            embeddings = Janghu.embed_model.encode(titles, convert_to_tensor=True)
            current_emb = embeddings[-1]
            existing_embs = embeddings[:-1]
            sims = Janghu.util.cos_sim(current_emb, existing_embs)[0]
            if any(float(sim) >= 0.82 for sim in sims):
                is_duplicate = True
                
        if is_duplicate:
            continue
            
        selected_news.append(news)
        global_links_jh.add(link)
        if len(selected_news) >= 5:
            break
            
    routed_data_jh[sector] = selected_news

final_data_jh = Janghu.deduplicate_routed_news(routed_data_jh, dedup_threshold=0.65)
final_report_jh = Janghu.generate_summary_with_gemini(final_data_jh)

with open(MD_JANGHU_MODIFIED, "w", encoding="utf-8") as f:
    f.write(f"# 금일 부각된 뉴스 (장후_수정)\n")
    f.write(f"> 수집 시간: 2026-07-31 00:00 ~ 2026-07-31 23:59\n\n")
    f.write(final_report_jh)

print(f"✅ 7월 31일 장후_수정.md 파일 생성 완료! ({MD_JANGHU_MODIFIED})")


# 2. 7/31 장전 수정 리포트 생성
print("\n--------------------------------------------------")
print("📥 [2/2] 7월 31일 장전 뉴스 수집 & 하이브리드 라우팅 진행 중...")
print("--------------------------------------------------")

start_time_jj = datetime(2026, 7, 30, 18, 0, 0)
end_time_jj = datetime(2026, 7, 31, 8, 30, 0)

raw_news_jj, foreign_jj = collect_news_for_module(Jangjeon, start_time_jj, end_time_jj)

routed_domestic_jj = Jangjeon.route_news_by_similarity(raw_news_jj, threshold=0.59, skip_sectors=["해외 이슈"])
routed_foreign_jj = {}
if foreign_jj:
    routed_foreign_jj = Jangjeon.route_news_by_similarity(foreign_jj, threshold=0.60)

routed_data_jj = {}
global_links_jj = set()

for sector in SECTOR_ORDER:
    merged_list = routed_domestic_jj.get(sector, []) + routed_foreign_jj.get(sector, [])
    merged_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    selected_news = []
    for news in merged_list:
        link = news.get("link", "")
        if link in global_links_jj:
            continue
            
        is_duplicate = False
        if selected_news:
            titles = [n["title"] for n in selected_news] + [news["title"]]
            embeddings = Jangjeon.embed_model.encode(titles, convert_to_tensor=True)
            current_emb = embeddings[-1]
            existing_embs = embeddings[:-1]
            sims = Jangjeon.util.cos_sim(current_emb, existing_embs)[0]
            if any(float(sim) >= 0.82 for sim in sims):
                is_duplicate = True
                
        if is_duplicate:
            continue
            
        selected_news.append(news)
        global_links_jj.add(link)
        if len(selected_news) >= 5:
            break
            
    routed_data_jj[sector] = selected_news

final_data_jj = Jangjeon.deduplicate_routed_news(routed_data_jj, dedup_threshold=0.65)
final_report_jj = Jangjeon.generate_summary_with_gemini(final_data_jj)

with open(MD_JANGJEON_MODIFIED, "w", encoding="utf-8") as f:
    f.write(f"# 장전 주요 뉴스 브리핑 (장전_수정)\n")
    f.write(f"> 수집 시간: 2026-07-30 18:00 ~ 2026-07-31 08:30\n\n")
    f.write(final_report_jj)

print(f"✅ 7월 31일 장전_수정.md 파일 생성 완료! ({MD_JANGJEON_MODIFIED})")

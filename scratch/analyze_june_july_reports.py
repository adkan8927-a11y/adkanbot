import os
import glob
import re

reports_dir = "reports"
files = glob.glob("reports/**/*.md", recursive=True) + glob.glob("reports/*.md")

print(f"🔍 총 {len(files)}개 파이프라인 생성 마크다운 보고서 스캔 시작...")

sector_articles = {}
file_sector_map = []

for fpath in sorted(set(files)):
    if "index.html" in fpath or "README" in fpath:
        continue
    rel_path = os.path.relpath(fpath, os.getcwd())
    fname = os.path.basename(fpath)
    
    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    current_sector = None
    for line in lines:
        line_str = line.strip()
        if line_str.startswith("### "):
            current_sector = line_str.replace("### ", "").strip()
            if current_sector not in sector_articles:
                sector_articles[current_sector] = []
        elif line_str.startswith("*   [") and current_sector:
            # extract markdown link
            m = re.match(r'\*\s+\[(.*?)\]\((.*?)\)', line_str)
            if m:
                title = m.group(1).replace("\\[", "[").replace("\\]", "]")
                link = m.group(2)
                sector_articles[current_sector].append({
                    "file": fname,
                    "rel_path": rel_path,
                    "sector": current_sector,
                    "title": title,
                    "link": link
                })

print(f"\n📊 총 섹터 수: {len(sector_articles)}개")
for sec, items in sector_articles.items():
    print(f"  - [{sec}]: 총 {len(items)}건")

# ==========================================
# 2. 섹터별 오분류 의심 패턴 스캐너
# ==========================================
suspects = []

# 검증 규칙 정의 (단어가 다른 섹터에 배치되어 있으면 오분류 의심)
check_rules = [
    # (검사할 타겟 룰 이름, 포함되면 올바른 섹터, [해당 단어 키워드], [제외할 섹터들])
    ("부동산 오분류", "부동산", ["아파트", "전세", "주담대", "집값", "청약", "미분양", "주택 준공", "재건축"], ["부동산"]),
    ("바이오 오분류", "BIO / 의료AI", ["유전자", "단백질 공학", "바이오", "신약", "임상", "치료제", "fda", "펩타이드", "질환", "바이오시밀러"], ["BIO / 의료AI"]),
    ("코인 오분류", "코인 / STO", ["비트코인", "가상자산", "토큰증권", "sto", "크립토", "이더리움", "리플", "블록체인", "토큰화", "rwa", "스테이블코인"], ["코인 / STO"]),
    ("공시/자사주 오분류", "M&A / 주요 공시", ["자사주", "주주환원", "밸류업", "무상증자", "유상증자", "자사주 소각", "ipo"], ["M&A / 주요 공시"]),
    ("반도체 오분류", "반도체", ["반도체", "hbm", "dram", "d램", "낸드", "삼성전자", "sk하이닉스", "파운드리", "cxmt", "ymtc", "tsmc", "마이크론"], ["반도체"]),
    ("이차전지 오분류", "이차전지", ["배터리", "이차전지", "전고체", "양극재", "음극재", "lg에너지솔루션", "sk온", "삼성sdi"], ["이차전지", "자동차"]),
    ("자동차 오분류", "자동차", ["현대차", "기아", "완성차", "도요타", "마스오토", "모빌리티"], ["자동차", "반도체"]),
    ("AI/로봇 오분류", "AI / 로봇", ["휴머노이드", "llm", "chatgpt", "생성형 ai", "에이전틱 ai"], ["AI / 로봇"]),
    ("원자재 오분류", "원자재", ["구리", "철강", "알루미늄", "희토류", "유가", "석유", "가스", "에너지", "광물", "리튬", "니켈"], ["원자재", "전력 / 에너지"]),
    ("방산 오분류", "국방 / 방산", ["k-방산", "미사일", "방위산업", "방사청", "kddx"], ["국방 / 방산", "조선 / 해운"]),
    ("조선 오분류", "조선 / 해운", ["lng선", "컨테이너선", "유조선", "조선 빅3"], ["조선 / 해운"]),
]

for sec, items in sector_articles.items():
    for item in items:
        title = item["title"]
        title_lower = title.lower()
        
        for rule_name, target_sec, keywords, allowed_secs in check_rules:
            if sec in allowed_secs:
                continue
            for kw in keywords:
                if kw in title_lower:
                    # 예외 룰 점검 (예: 미국 경제 기사에 단순 미국 언급 제외)
                    suspects.append({
                        "rule": rule_name,
                        "file": item["file"],
                        "current_sector": sec,
                        "suggested_sector": target_sec,
                        "keyword": kw,
                        "title": title
                    })
                    break

print(f"\n🚨 오분류 의심 기사 총 {len(suspects)}건 발견!")
for idx, s in enumerate(suspects, 1):
    print(f"{idx}. [{s['file']}] '{s['title'][:40]}' | 현: [{s['current_sector']}] ➔ 추천: [{s['suggested_sector']}] (키워드: {s['keyword']})")

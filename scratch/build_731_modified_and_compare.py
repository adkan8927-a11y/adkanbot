import os
import glob
import re
import importlib.util

print("🚀 7월 31일 장전 & 장후 수정 리포트 생성 및 전후 정밀 비교 분석 시작...")

def import_script(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

Janghu = import_script("Janghu", "데일리뉴스(장후).py")
Jangjeon = import_script("Jangjeon", "데일리뉴스(장전).py")

def process_markdown_file(input_path, output_path, mod_func):
    if not os.path.exists(input_path):
        print(f"⚠️ 파일 없음: {input_path}")
        return {}
        
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    header_lines = []
    sector_data = {}
    SECTOR_ORDER = [
        "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
        "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
        "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
        "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
    ]
    for s in SECTOR_ORDER:
        sector_data[s] = []
        
    current_sec = None
    for line in lines:
        line_str = line.strip()
        if line_str.startswith("# ") or line_str.startswith("> "):
            header_lines.append(line)
        elif line_str.startswith("### "):
            current_sec = line_str.replace("### ", "").strip()
        elif line_str.startswith("*   [") and current_sec:
            m = re.match(r'\*\s+\[(.*?)\]\((.*?)\)', line_str)
            if m:
                title = m.group(1).replace("\\[", "[").replace("\\]", "]")
                link = m.group(2)
                
                # 26개 섹터 + Gemini AI 2.5 Rescuer 하이브리드 재검증
                news_item = {"title": title, "desc": "", "link": link}
                new_sec = mod_func.check_and_adjust_sector(news_item, current_sec)
                
                if new_sec not in sector_data:
                    sector_data[new_sec] = []
                sector_data[new_sec].append({"title": title, "link": link, "orig_sector": current_sec})

    # 마크다운 렌더링
    new_md = []
    if "장후" in input_path:
        new_md.append("# 금일 부각된 뉴스 (장후_수정)\n> 수집 시간: 2026-07-31 00:00 ~ 2026-07-31 23:59\n\n")
    else:
        new_md.append("# 장전 주요 뉴스 브리핑 (장전_수정)\n> 수집 시간: 2026-07-30 18:00 ~ 2026-07-31 08:30\n\n")

    for sec in SECTOR_ORDER:
        new_md.append(f"### {sec}\n")
        items = sector_data.get(sec, [])
        if not items:
            new_md.append("--------\n\n")
        else:
            seen_titles = set()
            count = 0
            for item in items:
                title = item["title"]
                link = item["link"]
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                title_escaped = title.replace("[", "\\[").replace("]", "\\]")
                new_md.append(f"*   [{title_escaped}]({link})\n")
                count += 1
            if count == 0:
                new_md.pop()
                new_md.append("--------\n")
            new_md.append("\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(new_md)
        
    print(f"✅ 리포트 생성 완료: {output_path}")
    return sector_data

# 1. 7/31 장후_수정.md 및 장전_수정.md 생성
sec_data_jh = process_markdown_file("reports/2026-07-31_장후.md", "reports/2026-07-31_장후_수정.md", Janghu)
sec_data_jj = process_markdown_file("reports/2026-07-31_장전.md", "reports/2026-07-31_장전_수정.md", Jangjeon)

print("🎉 7월 31일 장전_수정.md & 장후_수정.md 생성 완료!")

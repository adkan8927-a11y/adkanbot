import os
import re

print("📊 7월 31일 기존 리포트 vs 26개 섹터 Gemini AI 하이브리드 수정 리포트 비교 분석 중...")

def parse_report(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    sectors = {}
    current_sec = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("### "):
            current_sec = line.replace("### ", "").strip()
            sectors[current_sec] = []
        elif line.startswith("*   [") and current_sec:
            m = re.match(r'\*\s+\[(.*?)\]\((.*?)\)', line)
            if m:
                title = m.group(1).replace("\\[", "[").replace("\\]", "]")
                link = m.group(2)
                sectors[current_sec].append((title, link))
    return sectors

janghu_orig = parse_report("reports/2026-07-31_장후.md")
janghu_mod = parse_report("reports/2026-07-31_장후_수정.md")

jangjeon_orig = parse_report("reports/2026-07-31_장전.md")
jangjeon_mod = parse_report("reports/2026-07-31_장전_수정.md")

diff_report_lines = []
diff_report_lines.append("# 📊 7월 31일 리포트 기존 vs 하이브리드 수정본 정밀 비교 보고서\n")
diff_report_lines.append("> 본 보고서는 새로 탑재된 **26개 섹터 핀포인트 보정 매트릭스 + Gemini AI 2.5 Rescuer 하이브리드 라우팅 파이프라인**을 구동하여 생성된 `2026-07-31_장전_수정.md` 및 `2026-07-31_장후_수정.md`와 기존 리포트를 비교 분석한 결과입니다.\n\n")

# 1. 장후 비교
diff_report_lines.append("## 🌆 1. [장후 리포트] 2026-07-31_장후.md vs 2026-07-31_장후_수정.md\n")

tot_orig_jh = sum(len(v) for v in janghu_orig.values())
tot_mod_jh = sum(len(v) for v in janghu_mod.values())

diff_report_lines.append(f"- **기존 장후 리포트 기사 수**: 총 {tot_orig_jh}건\n")
diff_report_lines.append(f"- **하이브리드 수정 장후 리포트 기사 수**: 총 {tot_mod_jh}건\n\n")
diff_report_lines.append("| 섹터명 | 기존 기사 수 | 수정본 기사 수 | 변동 내용 및 AI 보정 포인트 |\n")
diff_report_lines.append("| :--- | :---: | :---: | :--- |\n")

all_secs = sorted(set(list(janghu_orig.keys()) + list(janghu_mod.keys())))
for sec in all_secs:
    orig_items = janghu_orig.get(sec, [])
    mod_items = janghu_mod.get(sec, [])
    orig_count = len(orig_items)
    mod_count = len(mod_items)
    
    orig_titles = set(t[0] for t in orig_items)
    mod_titles = set(t[0] for t in mod_items)
    
    added = mod_titles - orig_titles
    removed = orig_titles - mod_titles
    
    notes = []
    if added:
        notes.append(f"✨ 신규/보정 채택: {len(added)}건")
    if removed:
        notes.append(f"🧹 중복/오분류 제거: {len(removed)}건")
    if not notes and orig_count == mod_count:
        notes.append("✅ 동일 유지")
        
    diff_report_lines.append(f"| **{sec}** | {orig_count}건 | {mod_count}건 | {', '.join(notes)} |\n")

# 2. 장전 비교
diff_report_lines.append("\n## 🌅 2. [장전 리포트] 2026-07-31_장전.md vs 2026-07-31_장전_수정.md\n")

tot_orig_jj = sum(len(v) for v in jangjeon_orig.values())
tot_mod_jj = sum(len(v) for v in jangjeon_mod.values())

diff_report_lines.append(f"- **기존 장전 리포트 기사 수**: 총 {tot_orig_jj}건\n")
diff_report_lines.append(f"- **하이브리드 수정 장전 리포트 기사 수**: 총 {tot_mod_jj}건\n\n")
diff_report_lines.append("| 섹터명 | 기존 기사 수 | 수정본 기사 수 | 변동 내용 및 AI 보정 포인트 |\n")
diff_report_lines.append("| :--- | :---: | :---: | :--- |\n")

all_secs_jj = sorted(set(list(jangjeon_orig.keys()) + list(jangjeon_mod.keys())))
for sec in all_secs_jj:
    orig_items = jangjeon_orig.get(sec, [])
    mod_items = jangjeon_mod.get(sec, [])
    orig_count = len(orig_items)
    mod_count = len(mod_items)
    
    orig_titles = set(t[0] for t in orig_items)
    mod_titles = set(t[0] for t in mod_items)
    
    added = mod_titles - orig_titles
    removed = orig_titles - mod_titles
    
    notes = []
    if added:
        notes.append(f"✨ 신규/보정 채택: {len(added)}건")
    if removed:
        notes.append(f"🧹 중복/오분류 제거: {len(removed)}건")
    if not notes and orig_count == mod_count:
        notes.append("✅ 동일 유지")
        
    diff_report_lines.append(f"| **{sec}** | {orig_count}건 | {mod_count}건 | {', '.join(notes)} |\n")

output_diff_file = "reports/2026-07-31_수정_비교_보고서.md"
with open(output_diff_file, "w", encoding="utf-8") as f:
    f.writelines(diff_report_lines)

print(f"🎉 정밀 비교 보고서 생성 완료! ({output_diff_file})")

import re
from datetime import datetime, timedelta

# 1. Update 데일리뉴스(주말).py
with open("데일리뉴스(주말).py", "r", encoding="utf-8") as f:
    weekend_code = f.read()

weekend_code = weekend_code.replace('_주말.md', '_위클리브리핑.md')
weekend_code = weekend_code.replace('_주말.html', '_위클리브리핑.html')
# Also rename any "주말" mentions in file paths if needed, wait, line 100-104 has:
# file_name = f"reports/{report_date}_주말.html"
weekend_code = weekend_code.replace('file_name = f"reports/{report_date}_주말.html"', 'file_name = f"reports/{report_date}_위클리브리핑.html"')
with open("데일리뉴스(주말).py", "w", encoding="utf-8") as f:
    f.write(weekend_code)


# 2. Update schedule_orchestrator.py
with open("schedule check/schedule_orchestrator.py", "r", encoding="utf-8") as f:
    sched_code = f.read()

# Remove the beta section
beta_start = sched_code.find("        <!-- 🧪 로컬 신규 수집 에이전트 4종 (베타테스트) -->")
beta_end = sched_code.find("        </div>", beta_start)
if beta_start != -1 and beta_end != -1:
    beta_end = sched_code.find("        </div>", beta_end + 10) # to capture the end of the beta section
    # Let's use regex to remove the beta section block
    sched_code = re.sub(r'        <!-- 🧪 로컬 신규 수집 에이전트 4종 \(베타테스트\) -->.*?</div>\s*</div>', '', sched_code, flags=re.DOTALL)

with open("schedule check/schedule_orchestrator.py", "w", encoding="utf-8") as f:
    f.write(sched_code)


# 3. Update generate_index.py
with open("generate_index.py", "r", encoding="utf-8") as f:
    gen_code = f.read()

# a. Remove section_beta_html logic
gen_code = re.sub(r'# 베타테스트 신규 4종 섹션 HTML 조립\s*section_beta_html = """.*?"""', 'section_beta_html = ""', gen_code, flags=re.DOTALL)
gen_code = gen_code.replace('{section_beta_html}', '')

# b. Remove weekly briefing banner
banner_pattern = r'<a href="\{latest_weekly_path\}".*?</a>'
gen_code = re.sub(banner_pattern, '', gen_code, flags=re.DOTALL)

# c. Update screener logic (1 column, next business day)
# Python part for next business day:
python_screener_mod = """                snap_data = json.load(f)
                scr_date_str = snap_data.get("scr_date", "최신")
                
                # Next Business Day calculation
                try:
                    scr_dt = datetime.strptime(scr_date_str, "%Y-%m-%d")
                    if scr_dt.weekday() == 4: # Friday
                        next_dt = scr_dt + timedelta(days=3)
                    elif scr_dt.weekday() == 5: # Saturday
                        next_dt = scr_dt + timedelta(days=2)
                    else:
                        next_dt = scr_dt + timedelta(days=1)
                    trade_date_str = next_dt.strftime("%y-%m-%d")
                except:
                    trade_date_str = snap_data.get("trade_date", "차일")"""

gen_code = re.sub(r'                snap_data = json\.load\(f\).*?trade_date_str = snap_data\.get\("trade_date", "차일"\)', python_screener_mod, gen_code, flags=re.DOTALL)

# HTML part for screener (flex column instead of grid)
screener_html_old = """<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;">"""
screener_html_new = """<div style="display: flex; flex-direction: column; gap: 1rem; max-width: 800px; margin: 0 auto;">"""
gen_code = gen_code.replace(screener_html_old, screener_html_new)

# d. Filter buttons (add 위클리브리핑)
buttons_old = """<div class="filter-buttons" style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                            <button class="filter-btn active" onclick="filterType('상한가', this)">🔥 당일상한가</button>"""
buttons_new = """<div class="filter-buttons" style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                            <button class="filter-btn" onclick="filterType('위클리', this)">📅 위클리브리핑</button>
                            <button class="filter-btn active" onclick="filterType('상한가', this)">🔥 당일상한가</button>"""
gen_code = gen_code.replace(buttons_old, buttons_new)

# e. JS logic update
js_old = """            const filtered = reportsData.filter(r => {
                if (r.type === '장중') return false;
                if (!r.date.startsWith(selectedMonth)) return false;
                
                if (currentFilter === 'all') return true;
                if (currentFilter === '상한가' && r.type === '당일상한가급등') return true;
                if (currentFilter === '매매' && (r.type === '스크리닝' || r.type === '피드백')) return true;
                if (currentFilter === '장전' && r.type === '장전') return true;
                if (currentFilter === '장후' && r.type === '장후') return true;
                if (currentFilter === '주말' && (r.type === '주말' || r.type === '위클리브리핑' || r.type === '5대섹터_통합분석')) return true;
                
                return false;
            });"""

js_new = """            const filtered = reportsData.filter(r => {
                if (r.type === '장중') return false;
                if (!r.date.startsWith(selectedMonth)) return false;
                
                if (currentFilter === '위클리' && (r.type === '위클리브리핑' || r.type === '5대섹터_통합분석')) return true;
                if (currentFilter === '상한가' && r.type === '당일상한가급등') return true;
                if (currentFilter === '매매' && (r.type === '스크리닝' || r.type === '피드백')) return true;
                if (currentFilter === '장전' && r.type === '장전') return true;
                if (currentFilter === '장후' && r.type === '장후') return true;
                if (currentFilter === '주말' && r.type === '주말') return true;
                
                return false;
            });"""
gen_code = gen_code.replace(js_old, js_new)

# Render logic
js_render_old = """                const card = document.createElement('div');
                card.className = 'card';
                let displayType = r.type;
                if(r.type === '당일상한가급등') displayType = '상한가/급등';
                if(r.type === '위클리브리핑' || r.type === '5대섹터_통합분석') displayType = '주말';
                
                card.innerHTML = `
                    <div class="card-header">
                        <span class="date-text">${r.date} (${weekday})</span>
                        <span class="badge ${r.type}">${displayType} 뉴스</span>
                    </div>"""

js_render_new = """                const card = document.createElement('div');
                card.className = 'card';
                let displayType = r.type;
                let displayDate = `${r.date} (${weekday})`;
                
                if(r.type === '당일상한가급등') displayType = '상한가/급등';
                if(r.type === '위클리브리핑' || r.type === '5대섹터_통합분석') {
                    displayType = '위클리브리핑';
                    // 주차 계산
                    const d = new Date(r.date);
                    const month = d.getMonth() + 1;
                    const week = Math.ceil((d.getDate() + 6 - d.getDay()) / 7);
                    displayDate = `${month}월 ${week}주차`;
                }
                
                card.innerHTML = `
                    <div class="card-header">
                        <span class="date-text">${displayDate}</span>
                        <span class="badge ${r.type}">${displayType}</span>
                    </div>"""
gen_code = gen_code.replace(js_render_old, js_render_new)

with open("generate_index.py", "w", encoding="utf-8") as f:
    f.write(gen_code)

print("All updates applied!")

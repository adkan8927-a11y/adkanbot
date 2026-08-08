import re

with open("generate_index.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update HTML
html_start = content.find('                <div class="reports-archive-layout">')
html_end = content.find('            </div>\n        </div>\n    </main>')

new_html = """                <div class="search-filter-container" style="justify-content: center; margin-bottom: 2rem;">
                    <div class="filter-buttons" style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-bottom: 1rem;">
                        <button class="filter-btn active" onclick="filterType('all', this)">전체</button>
                        <button class="filter-btn" onclick="filterType('상한가', this)">🔥 당일상한가</button>
                        <button class="filter-btn" onclick="filterType('매매', this)">💼 매매리포트</button>
                        <button class="filter-btn" onclick="filterType('장전', this)">🌅 장전</button>
                        <button class="filter-btn" onclick="filterType('장후', this)">🌆 장후</button>
                        <button class="filter-btn" onclick="filterType('주말', this)">📅 주말</button>
                    </div>
                </div>

                <div class="reports-archive-layout">
                    <aside class="month-sidebar">
                        <h3>📅 월별 아카이브</h3>
                        <ul id="monthList" class="month-list">
                            <!-- JS 동적 렌더링 -->
                        </ul>
                    </aside>
                    <div class="category-content" style="margin-bottom: 0;">
                        <div class="grid-container" id="reportsGrid">
                            <!-- 자바스크립트 동적 렌더링 -->
                        </div>
                        <button class="grid-toggle-btn" id="gridToggleBtn" onclick="toggleGridExpand()">
                            <span id="gridToggleLabel">▼ 더보기</span>
                        </button>
                    </div>
                </div>"""
if html_start != -1 and html_end != -1:
    content = content[:html_start] + new_html + "\n" + content[html_end:]

# 2. Update JS
js_start = content.find("        // --- 월별 사이드바 초기화 ---")
js_end = content.find("    </script>", js_start)

new_js = """        let selectedMonth = '';
        let currentFilter = 'all';
        let gridExpanded = false;
        const COLLAPSED_HEIGHT = '2400px';

        // --- 월별 사이드바 초기화 ---
        function initMonthSidebar() {{
            const monthsSet = new Set();
            reportsData.forEach(r => {{
                if(r.type === '장중') return; // 장중 제외
                const m = r.date.substring(0, 7); // YYYY-MM
                monthsSet.add(m);
            }});
            const availableMonths = Array.from(monthsSet).sort().reverse();
            
            const monthList = document.getElementById('monthList');
            if(availableMonths.length > 0) {{
                selectedMonth = availableMonths[0]; // 최신 월 기본 선택
            }}

            availableMonths.forEach(m => {{
                const li = document.createElement('li');
                li.className = `month-item ${{m === selectedMonth ? 'active' : ''}}`;
                li.textContent = m.replace('-', '년 ') + '월';
                li.onclick = () => {{
                    document.querySelectorAll('.month-item').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    selectedMonth = m;
                    renderReports();
                }};
                monthList.appendChild(li);
            }});
        }}

        function filterType(type, element) {{
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            renderReports();
        }}

        // --- 카테고리 & 월별 렌더링 ---
        function renderReports() {{
            const grid = document.getElementById('reportsGrid');
            grid.innerHTML = '';
            
            const filtered = reportsData.filter(r => {{
                if (r.type === '장중') return false;
                if (!r.date.startsWith(selectedMonth)) return false;
                
                if (currentFilter === 'all') return true;
                if (currentFilter === '상한가' && r.type === '당일상한가급등') return true;
                if (currentFilter === '매매' && (r.type === '스크리닝' || r.type === '피드백')) return true;
                if (currentFilter === '장전' && r.type === '장전') return true;
                if (currentFilter === '장후' && r.type === '장후') return true;
                if (currentFilter === '주말' && (r.type === '주말' || r.type === '위클리브리핑' || r.type === '5대섹터_통합분석')) return true;
                
                return false;
            }});

            if (filtered.length === 0) {{
                grid.innerHTML = `<div class="no-results">해당 조건에 맞는 리포트가 존재하지 않습니다.</div>`;
                document.getElementById('gridToggleBtn').style.display = 'none';
                return;
            }}

            filtered.forEach(r => {{
                const dateObj = new Date(r.date);
                const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
                const weekday = weekdays[dateObj.getDay()];
                
                const card = document.createElement('div');
                card.className = 'card';
                let displayType = r.type;
                if(r.type === '당일상한가급등') displayType = '상한가/급등';
                if(r.type === '위클리브리핑' || r.type === '5대섹터_통합분석') displayType = '주말';
                
                card.innerHTML = `
                    <div class="card-header">
                        <span class="date-text">${{r.date}} (${{weekday}})</span>
                        <span class="badge ${{r.type}}">${{displayType}} 뉴스</span>
                    </div>
                    <p>${{r.summary}}</p>
                    <a href="${{r.html_path}}" class="view-link">
                        리포트 보기
                        <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </a>
                `;
                grid.appendChild(card);
            }});

            gridExpanded = false;
            grid.style.maxHeight = COLLAPSED_HEIGHT;
            const btn = document.getElementById('gridToggleBtn');
            const label = document.getElementById('gridToggleLabel');
            if (grid.scrollHeight <= grid.clientHeight + 10) {{
                btn.style.display = 'none';
            }} else {{
                btn.style.display = 'flex';
                label.textContent = '▼ 더보기';
            }}
        }}

        function toggleGridExpand() {{
            const grid = document.getElementById('reportsGrid');
            const label = document.getElementById('gridToggleLabel');
            gridExpanded = !gridExpanded;
            if (gridExpanded) {{
                grid.style.maxHeight = grid.scrollHeight + 'px';
                label.textContent = '▲ 접기';
            }} else {{
                grid.style.maxHeight = COLLAPSED_HEIGHT;
                grid.scrollTop = 0;
                label.textContent = '▼ 더보기';
            }}
        }}

        // 초기 렌더링
        window.onload = () => {{
            initTicker();
            initMonthSidebar();
            renderReports();
        }};
"""
if js_start != -1 and js_end != -1:
    content = content[:js_start] + new_js + "\n" + content[js_end:]

with open("generate_index.py", "w", encoding="utf-8") as f:
    f.write(content)
print("generate_index.py updated layout correctly!")

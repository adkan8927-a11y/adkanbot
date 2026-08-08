import re

with open("generate_index.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix CSS braces
css_block_start = content.find("/* 새로운 아카이브 레이아웃 스타일 (데스크탑 기본) */")
css_block_end = content.find(".badge.피드백 {{")
if css_block_start != -1 and css_block_end != -1:
    css_section = content[css_block_start:css_block_end]
    css_section_fixed = css_section.replace("{", "{{").replace("}", "}}")
    content = content[:css_block_start] + css_section_fixed + content[css_block_end:]

# 2. Fix JS logic
js_block_start = content.find("        let currentFilter = 'all';")
js_block_end = content.find("    </script>", js_block_start)

new_js = """        // --- 티커 배너 로직 ---
        let currentTickerIndex = 0;
        
        function initTicker() {{
            const viewport = document.getElementById('tickerViewport');
            if (!tickerData || tickerData.length === 0) {{
                viewport.innerHTML = `<div class="ticker-item active"><span class="ticker-text">예정된 주요 일정이 없습니다.</span></div>`;
                return;
            }}
            
            // 초기 DOM 생성
            tickerData.forEach((item, index) => {{
                const el = item.link && item.link !== 'nan' ? document.createElement('a') : document.createElement('div');
                el.className = `ticker-item ${{index === 0 ? 'active' : ''}}`;
                el.id = `ticker-item-${{index}}`;
                if (item.link && item.link !== 'nan') {{
                    el.href = item.link;
                    el.target = "_blank";
                    el.style.textDecoration = "none";
                }}
                el.innerHTML = `
                    <span class="ticker-badge">${{item.badge}}</span>
                    <span class="ticker-date">${{item.date}}</span>
                    <span class="ticker-text">${{item.text}}</span>
                `;
                viewport.appendChild(el);
            }});
            
            if (tickerData.length > 1) {{
                setInterval(rotateTicker, 3500); // 3.5초마다 회전
            }}
        }}
        
        function rotateTicker() {{
            const prevIndex = currentTickerIndex;
            currentTickerIndex = (currentTickerIndex + 1) % tickerData.length;
            
            const prevEl = document.getElementById(`ticker-item-${{prevIndex}}`);
            const nextEl = document.getElementById(`ticker-item-${{currentTickerIndex}}`);
            
            // 이전 요소는 아래로 빠짐
            prevEl.className = 'ticker-item exit';
            
            // 다음 요소는 위에서 들어옴
            // 브라우저 렌더링 사이클을 위해 잠시 대기 후 active 클래스 부여
            nextEl.className = 'ticker-item'; 
            setTimeout(() => {{
                nextEl.className = 'ticker-item active';
            }}, 50);
        }}

        let selectedMonth = '';

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
                    renderMonthReports();
                }};
                monthList.appendChild(li);
            }});
        }}

        // --- 카테고리별 렌더링 ---
        function renderMonthReports() {{
            const containerSurge = document.getElementById('grid-surge');
            const containerTrading = document.getElementById('grid-trading');
            const containerMorning = document.getElementById('grid-morning');
            const containerEvening = document.getElementById('grid-evening');
            const containerWeekend = document.getElementById('grid-weekend');
            
            // 초기화
            [containerSurge, containerTrading, containerMorning, containerEvening, containerWeekend].forEach(c => {{
                if (c) c.innerHTML = '';
            }});

            let counts = {{ surge: 0, trading: 0, morning: 0, evening: 0, weekend: 0 }};

            reportsData.forEach(r => {{
                if(r.type === '장중') return;
                if(!r.date.startsWith(selectedMonth)) return;

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

                if(r.type === '당일상한가급등') {{
                    if(containerSurge) containerSurge.appendChild(card);
                    counts.surge++;
                }} else if(r.type === '스크리닝' || r.type === '피드백') {{
                    if(containerTrading) containerTrading.appendChild(card);
                    counts.trading++;
                }} else if(r.type === '장전') {{
                    if(containerMorning) containerMorning.appendChild(card);
                    counts.morning++;
                }} else if(r.type === '장후') {{
                    if(containerEvening) containerEvening.appendChild(card);
                    counts.evening++;
                }} else if(r.type === '주말' || r.type === '위클리브리핑' || r.type === '5대섹터_통합분석') {{
                    if(containerWeekend) containerWeekend.appendChild(card);
                    counts.weekend++;
                }}
            }});

            // 빈 섹션 숨김 처리
            if (document.getElementById('cat-surge')) document.getElementById('cat-surge').style.display = counts.surge > 0 ? 'block' : 'none';
            if (document.getElementById('cat-trading')) document.getElementById('cat-trading').style.display = counts.trading > 0 ? 'block' : 'none';
            if (document.getElementById('cat-morning')) document.getElementById('cat-morning').style.display = counts.morning > 0 ? 'block' : 'none';
            if (document.getElementById('cat-evening')) document.getElementById('cat-evening').style.display = counts.evening > 0 ? 'block' : 'none';
            if (document.getElementById('cat-weekend')) document.getElementById('cat-weekend').style.display = counts.weekend > 0 ? 'block' : 'none';
        }}

        // 초기 렌더링
        window.onload = () => {{
            initTicker();
            initMonthSidebar();
            renderMonthReports();
        }};
"""
content = content[:js_block_start] + new_js + content[js_block_end:]

with open("generate_index.py", "w", encoding="utf-8") as f:
    f.write(content)
print("generate_index.py successfully patched!")

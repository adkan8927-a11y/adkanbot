import re

with open("generate_index.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update CSS
css_target = """        /* 새로운 아카이브 레이아웃 스타일 (데스크탑 기본) */
        .reports-archive-layout {{
            display: grid;
            grid-template-columns: 220px 1fr;
            gap: 2rem;
            margin-top: 1rem;
            align-items: start;
        }}

        .month-sidebar {{
            background: #ffffff;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.2rem;
            position: sticky;
            top: 2rem;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
        }}"""

new_css = """        /* 통합 아카이브 패널 스타일 */
        .archive-panel {{
            background: #ffffff;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
            overflow: hidden;
            margin-bottom: 3rem;
            margin-top: 1rem;
        }}

        .archive-header {{
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            padding: 1.2rem;
            display: flex;
            justify-content: center;
        }}

        .reports-archive-layout {{
            display: flex;
            flex-direction: row;
            align-items: stretch;
            min-height: 500px;
        }}

        .month-sidebar {{
            width: 220px;
            flex-shrink: 0;
            background: #ffffff;
            border-right: 1px solid #e2e8f0;
            padding: 1.5rem;
        }}"""

content = content.replace(css_target, new_css)

# Update mobile CSS
mobile_css_target = """            .reports-archive-layout {{
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }}
            .month-sidebar {{
                position: static;
                padding: 0.5rem;
            }}"""
mobile_css_new = """            .reports-archive-layout {{
                flex-direction: column;
                min-height: auto;
            }}
            .month-sidebar {{
                width: 100%;
                border-right: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 1rem;
            }}
            .archive-header {{
                padding: 1rem 0.5rem;
            }}
            .category-content {{
                padding: 1rem !important;
            }}"""
content = content.replace(mobile_css_target, mobile_css_new)


# Update category-content CSS
cat_content_target = """        .category-section {{
            margin-bottom: 3.5rem;
        }}"""
cat_content_new = """        .category-content {{
            flex-grow: 1;
            padding: 1.5rem;
            background: #fafaf9;
        }}
        
        .category-section {{
            margin-bottom: 3.5rem;
        }}"""
content = content.replace(cat_content_target, cat_content_new)

# 2. Update HTML
html_start = content.find('                <div class="search-filter-container"')
html_end = content.find('            </div>\n        </div>\n    </main>')

new_html = """                <div class="archive-panel">
                    <div class="archive-header">
                        <div class="filter-buttons" style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                            <button class="filter-btn active" onclick="filterType('상한가', this)">🔥 당일상한가</button>
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
                        <div class="category-content">
                            <div class="grid-container" id="reportsGrid">
                                <!-- 자바스크립트 동적 렌더링 -->
                            </div>
                            <button class="grid-toggle-btn" id="gridToggleBtn" onclick="toggleGridExpand()">
                                <span id="gridToggleLabel">▼ 더보기</span>
                            </button>
                        </div>
                    </div>
                </div>"""
if html_start != -1 and html_end != -1:
    content = content[:html_start] + new_html + "\n" + content[html_end:]

with open("generate_index.py", "w", encoding="utf-8") as f:
    f.write(content)
print("generate_index.py layout fixed to table design!")

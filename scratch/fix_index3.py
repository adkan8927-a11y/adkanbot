import re

with open("generate_index.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix duplicated let selectedMonth
content = content.replace("        let selectedMonth = '';\n\n        let selectedMonth = '';", "        let selectedMonth = '';")

# Fix currentFilter default
content = content.replace("let currentFilter = 'all';", "let currentFilter = '상한가';")

# Remove "전체" button and make "당일상한가" active
old_buttons = """                        <button class="filter-btn active" onclick="filterType('all', this)">전체</button>
                        <button class="filter-btn" onclick="filterType('상한가', this)">🔥 당일상한가</button>"""
new_buttons = """                        <button class="filter-btn active" onclick="filterType('상한가', this)">🔥 당일상한가</button>"""
content = content.replace(old_buttons, new_buttons)

with open("generate_index.py", "w", encoding="utf-8") as f:
    f.write(content)
print("generate_index.py fixed!")

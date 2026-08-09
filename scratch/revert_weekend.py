with open("데일리뉴스(주말).py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace('_위클리브리핑.md', '_주말.md')
code = code.replace('_위클리브리핑.html', '_주말.html')
code = code.replace('file_name = f"reports/{report_date}_위클리브리핑.html"', 'file_name = f"reports/{report_date}_주말.html"')

with open("데일리뉴스(주말).py", "w", encoding="utf-8") as f:
    f.write(code)

print("Reverted 데일리뉴스(주말).py")

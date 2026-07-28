import pdfplumber

with pdfplumber.open("20260630_보도자료_KSD_2026년_7월_의무보유등록_해제_예정.pdf") as pdf:
    page = pdf.pages[2]
    tables = page.extract_tables()
    for t in tables:
        print("TABLE START")
        for row in t[:5]:
            print(row)
        print("...")

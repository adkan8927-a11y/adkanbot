import pdfplumber

pdf_path = "20260630_보도자료_KSD_2026년_7월_의무보유등록_해제_예정.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        if tables:
            print(f"--- Page {i+1} Tables ---")
            for table in tables:
                for row in table[:3]:  # Print first 3 rows of each table
                    print(row)

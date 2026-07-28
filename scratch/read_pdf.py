import pdfplumber
import sys

with pdfplumber.open("20260630_보도자료_KSD_2026년_7월_의무보유등록_해제_예정.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        print(f"--- PAGE {i} ---")
        if text:
            print(text[:300]) # Print start of page to see what's on it

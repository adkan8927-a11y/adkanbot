import pandas as pd
from pathlib import Path

CSV_FILE = Path("reports/broker_upgrades.csv")
df = pd.read_csv(CSV_FILE)

# 1. Filter out empty title
target_df = df[df['리포트제목'].notna() & (df['리포트제목'].astype(str).str.strip() != '') & (df['리포트제목'].astype(str).str.strip() != 'nan')]

# 2. Sort by highest upgrade rate and drop duplicate titles per stock
target_df = target_df.sort_values(by="목표가상승률(%)", ascending=False).drop_duplicates(subset=['종목명', '리포트제목'], keep='first')

md = "| 종목 | 증권사 | 상승률(%) | 리포트 |\n"
md += "| :--- | :--- | :---: | :--- |\n"
for _, row in target_df.iterrows():
    title = str(row['리포트제목']).strip()
    link = str(row['PDF링크']).strip() if pd.notna(row['PDF링크']) else ""
    if link and link != "nan":
        title_fmt = f"[{title}]({link})"
    else:
        title_fmt = title
    md += f"| **{row['종목명']}** | {row['증권사']} | +{row['목표가상승률(%)']:.2f}% | {title_fmt} |\n"

print(md)

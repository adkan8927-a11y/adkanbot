import glob
import re
import json
import os

files = glob.glob("reports/202*-*-*_스크리닝.md")
latest_file = sorted(files)[-1]
scr_date = os.path.basename(latest_file).split("_")[0]
print(f"Latest file: {latest_file}, Date: {scr_date}")

with open(latest_file, "r", encoding="utf-8") as f:
    content = f.read()

results = {"1": [], "2": [], "3": []}
current_strategy = None

# Extract tables
import re
lines = content.split("\n")
for line in lines:
    if "전략 1 요약표" in line:
        current_strategy = "1"
    elif "전략 2 요약표" in line:
        current_strategy = "2"
    elif "전략 3 요약표" in line or "전략 3 —" in line:
        current_strategy = "3"
        
    if current_strategy and line.startswith("| **"):
        # | **삼성전자** (005930) | 231,250원 | +26.8% 장대양봉 | 3일선 | **★ TOP 1 선택** |
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            name = parts[1].replace("**", "").split(" ")[0].strip()
            close_str = parts[2].replace(",", "").replace("원", "").strip()
            try: close = int(close_str)
            except: close = 0
            reason = parts[3]
            ma = parts[4]
            status = parts[5]
            
            is_top = "TOP" in status
            is_candidate = "후보군" in status
            
            # Additional tags
            is_adk = "ADK" in reason or "ADK특" in status
            is_sawitgam = "사윗감" in status or "사윗감" in reason
            
            item = {
                "name": name,
                "close": close,
                "support_ma": ma,
                "reason": reason,
                "sawitgam": is_sawitgam,
                "is_adk_top1": is_adk,
                "frgn_20": 0.0,
                "orgn_20": 0.0,
                "is_top": is_top,
                "is_candidate": is_candidate
            }
            results[current_strategy].append(item)

print(json.dumps(results, ensure_ascii=False, indent=2))

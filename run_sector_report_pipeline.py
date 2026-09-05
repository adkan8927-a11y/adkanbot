"""
====================================================================
🚀 5대 핵심 섹터 통합 업황 분석 & 종목 맵핑 자동화 파이프라인
파일명: run_sector_report_pipeline.py
====================================================================
"""

import sys
import os
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

sys.path.append(str(BASE_DIR))

from collector import get_top_volume_stocks, get_all_ohlcv_cached
from screener import screen_3or5_ma_settle, screen_upper_limit_or_high29, is_valid_trading_stock
from sector_classifier import get_top_sectors, get_top5_sectors
from sector_analyzer import generate_single_markdown_table, get_dynamic_sector_info


def build_landscape_html_report(settle_top5: list, upper_top5: list, target_date: str) -> str:
    """260517 정리.pdf 고화질 랜드스케이프 프레젠테이션 디자인 HTML 생성"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280, initial-scale=1.0">
<title>5대 핵심 섹터 통합 업황 분석 및 종목 맵핑 ({target_date})</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Outfit:wght@700;800;900&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #0b0f19;
  --card-bg: rgba(22, 28, 45, 0.85);
  --card-border: rgba(255, 255, 255, 0.1);
  --accent-purple: #8b5cf6;
  --accent-blue: #3b82f6;
  --accent-gold: #f59e0b;
  --text: #f3f4f6;
  --muted: #9ca3af;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg); color: var(--text); font-family: 'Inter', 'AppleGothic', sans-serif;
  background-image: radial-gradient(circle at 10% 10%, rgba(139, 92, 246, 0.15) 0%, transparent 40%), radial-gradient(circle at 90% 90%, rgba(59, 130, 246, 0.12) 0%, transparent 40%);
  background-attachment: fixed; padding: 2rem;
}}
.container {{ max-width: 1400px; margin: 0 auto; }}
header {{ text-align: center; margin-bottom: 2.5rem; }}
.badge {{ display: inline-block; background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); color: #fff; padding: 0.4rem 1.4rem; border-radius: 50px; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.8rem; }}
h1 {{ font-family: 'Outfit', sans-serif; font-size: 2.8rem; font-weight: 900; background: linear-gradient(to right, #ffffff, #c7d2fe, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }}
.subtitle {{ color: var(--muted); font-size: 1rem; }}

.section-block {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 20px; padding: 2rem; margin-bottom: 3rem; backdrop-filter: blur(16px); box-shadow: 0 20px 40px rgba(0,0,0,0.4); }}
.section-title {{ font-family: 'Outfit', sans-serif; font-size: 1.8rem; font-weight: 800; margin-bottom: 1.5rem; color: #fff; display: flex; align-items: center; gap: 0.8rem; }}

table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; border-radius: 12px; overflow: hidden; }}
th {{ background: rgba(255, 255, 255, 0.06); color: #c7d2fe; font-size: 0.95rem; font-weight: 700; padding: 1rem 1.2rem; text-align: left; border-bottom: 2px solid var(--card-border); }}
td {{ padding: 1.2rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.9rem; line-height: 1.6; color: #e5e7eb; vertical-align: top; }}
tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}

.sector-cell {{ font-weight: 800; font-size: 1.05rem; color: #fbbf24; width: 18%; }}
.reason-cell {{ width: 38%; }}
.schedule-cell {{ width: 24%; color: #93c5fd; }}
.stocks-cell {{ width: 20%; color: #a7f3d0; font-weight: 600; word-break: keep-all; }}

footer {{ text-align: center; color: var(--muted); font-size: 0.85rem; margin-top: 2rem; padding: 1rem; }}
</style>
</head>
<body>

<div class="container">
  <header>
    <div class="badge">Market Intelligence Analysis</div>
    <h1>📊 5대 핵심 섹터 통합 업황 분석 및 종목 맵핑</h1>
    <p class="subtitle">기준일자: {target_date} | 생성시각: {now_str} | 파이프라인 자동화 리포트</p>
  </header>

  <div class="section-block">
    <div class="section-title">🔥 섹션 1. 지난주 상한가 또는 고가 29%+ 도달 5대 핵심 섹터</div>
    <table>
      <thead>
        <tr>
          <th>섹터명</th>
          <th>강했던 이유 및 핵심 업황</th>
          <th>주요 일정</th>
          <th>종목명</th>
        </tr>
      </thead>
      <tbody>
"""
    for sec in upper_top5:
        sname = sec["sector_name"]
        stk_list = sec["stocks"]
        stk_str = ", ".join(stk_list) if stk_list else "대표 주도 종목"
        info = get_dynamic_sector_info(sname, stk_list, target_date=target_date)
        html += f"""
        <tr>
          <td class="sector-cell">{sname}</td>
          <td class="reason-cell">{info['reason']}</td>
          <td class="schedule-cell">{info['schedule']}</td>
          <td class="stocks-cell">{stk_str}</td>
        </tr>
"""
    html += """
      </tbody>
    </table>
  </div>

  <div class="section-block">
    <div class="section-title">📌 섹션 2. 최근 3일선 또는 5일선 안착 5대 핵심 섹터</div>
    <table>
      <thead>
        <tr>
          <th>섹터명</th>
          <th>강했던 이유 및 핵심 업황</th>
          <th>주요 일정</th>
          <th>종목명</th>
        </tr>
      </thead>
      <tbody>
"""
    for sec in settle_top5:
        sname = sec["sector_name"]
        stk_list = sec["stocks"]
        stk_str = ", ".join(stk_list) if stk_list else "대표 주도 종목"
        info = get_dynamic_sector_info(sname, stk_list, target_date=target_date)
        html += f"""
        <tr>
          <td class="sector-cell">{sname}</td>
          <td class="reason-cell">{info['reason']}</td>
          <td class="schedule-cell">{info['schedule']}</td>
          <td class="stocks-cell">{stk_str}</td>
        </tr>
"""
    html += """
      </tbody>
    </table>
  </div>

  <footer>
    adkan연구3 자동화 파이프라인 | 엑셀 바로 붙여넣기 마크다운 표 100% 지원
  </footer>
</div>

</body>
</html>
"""
    return html


def run_pipeline(target_date: str = "2026-07-31", mode: str = "all", limit: int = 2600):
    print("=" * 70)
    print(f"🚀 [주말 5대 핵심 섹터 통합 업황 분석 파이프라인] (기준일: {target_date}, KRX 전종목 스캔)")
    print("=" * 70)

    # 1. KRX 전종목 일봉 Parquet 데이터 로딩
    cache_2600 = BASE_DIR / "data_cache" / f"ohlcv_2600_{target_date}.parquet"
    if cache_2600.exists():
        print(f"⚡ [Parquet Cache HIT] KRX 전종목 일봉 데이터 초고속 로딩: {cache_2600.name}")
        full_df = pd.read_parquet(cache_2600)
        ohlcv_dict = {}
        for code, group in full_df.groupby("Code"):
            ohlcv_dict[str(code).zfill(6)] = group.drop(columns=["Code"])
        
        # 종목 정보 구성
        from collector import get_stock_list
        stocks_df = get_stock_list()
    else:
        stocks_df = get_top_volume_stocks(limit=limit)
        ohlcv_dict = get_all_ohlcv_cached(stocks_df, target_date=target_date, count=320)

    date_ts = pd.to_datetime(target_date)
    settle_stocks = []
    upper_stocks = []

    # 2. 스크리닝 진행
    for idx, row in stocks_df.iterrows():
        code = str(row['Code']).zfill(6)
        name = row.get('Name', code)
        df = ohlcv_dict.get(code, pd.DataFrame())

        if df.empty:
            continue

        if date_ts in df.index:
            day_idx = df.index.get_loc(date_ts)
            df_slice = df.iloc[:day_idx + 1]
        else:
            df_slice = df

        if df_slice.empty:
            continue

        # 유저 지정 제외 종목 필터링 (우선주, 관리, 환기, 정리매매, 거래정지, 단일가 제외 / 투자경고,주의,위험 포함)
        if not is_valid_trading_stock(name, code, df_slice):
            continue

        latest = df_slice.iloc[-1]
        amount_100m = round(latest.get("Amount", 0) / 100_000_000, 1)

        res_settle = screen_3or5_ma_settle(df_slice)
        if res_settle:
            res_settle["name"] = name
            res_settle["code"] = code
            res_settle["amount_100m"] = amount_100m
            settle_stocks.append(res_settle)

        res_upper = screen_upper_limit_or_high29(df_slice)
        if res_upper:
            res_upper["name"] = name
            res_upper["code"] = code
            res_upper["amount_100m"] = amount_100m
            upper_stocks.append(res_upper)

    print(f"✅ 스크리닝 포착 완료 (3/5일선 안착: {len(settle_stocks)}개 / 지난주 상한가29%: {len(upper_stocks)}개)")

    # 3. 핵심 섹터 추출 (실제 포착 섹터만, 최대 5개)
    settle_top5 = get_top_sectors(settle_stocks, top_n=5)
    upper_top5 = get_top_sectors(upper_stocks, top_n=5)
    print(f"✅ 섹터 추출 완료 (상한가/29% 포착: {len(upper_top5)}개 섹터 / 3·5일선 안착: {len(settle_top5)}개 섹터)")

    # 4. 단일 마크다운 표 생성 (터미널 및 엑셀 지원)
    md_output = ""
    
    if mode in ["all", "upper_limit"]:
        n_upper = len(upper_top5)
        tbl_upper = generate_single_markdown_table(upper_top5, f"지난주 상한가/고가29% {n_upper}대 핵심 섹터 ({target_date})", target_date=target_date)
        md_output += tbl_upper

    if mode in ["all", "ma_settle"]:
        n_settle = len(settle_top5)
        tbl_settle = generate_single_markdown_table(settle_top5, f"최근 3일선 또는 5일선 안착 {n_settle}대 핵심 섹터 ({target_date})", target_date=target_date)
        md_output += tbl_settle

    print("\n" + "=" * 70)
    print("📋 [엑셀 바로 붙여넣기용 단일 마크다운 표 (Single Markdown Table)]")
    print("=" * 70 + "\n")
    print(md_output)

    # 5. MD & HTML 보고서 저장 (유저 지정 표준 규격: YYYY-MM-DD_위클리브리핑.md / .html)
    md_path = REPORTS_DIR / f"{target_date}_위클리브리핑.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_output)

    html_content = build_landscape_html_report(settle_top5, upper_top5, target_date)
    html_path = REPORTS_DIR / f"{target_date}_위클리브리핑.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"🎉 위클리 브리핑 리포트 생성 완수: {md_path.name} & {html_path.name}")
    print(f"   ├─ 상한가/29% 섹터: {[s['sector_name'] for s in upper_top5]}")
    print(f"   └─ 3·5일선 안착 섹터: {[s['sector_name'] for s in settle_top5]}")
    return md_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="5대 핵심 섹터 통합 업황 분석 파이프라인")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="기준일자 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument("--mode", type=str, default="all", choices=["all", "ma_settle", "upper_limit"], help="실행 모드")
    parser.add_argument("--limit", type=int, default=2600, help="스캔 종목 수 (기본 2,600개 KRX 전종목)")
    args = parser.parse_args()

    run_pipeline(target_date=args.date, mode=args.mode, limit=args.limit)

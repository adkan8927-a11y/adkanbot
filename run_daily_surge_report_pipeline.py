"""
🚀 당일 상한가/급등주 분석 파이프라인 (run_daily_surge_report_pipeline.py)

역할:
1. KRX 전종목 수집 및 당일 상한가/하한가 종목 및 150억+ 15%+ 급등주 탐색
2. 항목별 최대 5개 종목 선정 (베타테스트 요약)
3. 네이버 뉴스 기반 상승 이유 파싱 & 이평선 맞춤 차트 PNG 캡처
4. reports/YYYY-MM-DD_당일상한가급등.md & .html 조립 및 대시보드/Git Push 배포
"""

import sys
import os
import argparse
import time
import subprocess
import pandas as pd
import numpy as np

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = Path("/Users/adkan/adkan연구2")
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
CHARTS_DIR = BASE_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# reports 디렉토리 내 charts 심볼릭 링크 자동 보장
(REPORTS_DIR / "charts").unlink(missing_ok=True)
try:
    os.symlink(CHARTS_DIR, REPORTS_DIR / "charts")
except Exception:
    pass

sys.path.append(str(BASE_DIR))

# news_momentum_parser는 매매 엔진(연구3)에 위치 — 연구2에서 참조 시 경로 추가
RESEARCH3_DIR = Path("/Users/adkan/adkan연구3")
if RESEARCH3_DIR.exists() and str(RESEARCH3_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH3_DIR))

from collector import get_stock_list, get_all_ohlcv_cached, get_ohlcv
from news_momentum_parser import NewsMomentumParser
from chart_drawer import draw_and_save_chart_by_strategy, HAS_MPF

def fmt_amt(a):
    if a >= 100_000_000:
        return f"{a / 100_000_000:.1f}억"
    elif a >= 10_000:
        return f"{a / 10_000:.0f}만"
    return f"{a}원"


def generate_surge_chart(df: pd.DataFrame, code: str, name: str, date_str: str) -> str:
    """
    급등주 전용 일봉 차트 PNG 생성
    """
    clean_date = date_str.replace("-", "")
    filename = f"chart_surge_{clean_date}_{code}_{name}.png"
    filepath = CHARTS_DIR / filename
    rel_path = f"charts/{filename}"

    if filepath.exists() and filepath.stat().st_size > 1000:
        return rel_path

    try:
        saved_path = draw_and_save_chart_by_strategy(code, name, df, "당일급등분석", save_dir=CHARTS_DIR)
        if saved_path and os.path.exists(saved_path):
            os.rename(saved_path, str(filepath))
            return rel_path
    except Exception as e:
        print(f"⚠️ 차트 생성 경고 ({name}): {e}")

    return rel_path


def run_daily_surge_pipeline(target_date: str = None, max_upper: int = 5, max_surge: int = 10):
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    print(f"============================================================")
    print(f"🔥 [당일 상한가/급등주 파이프라인] 기준일: {target_date} (상한가: {max_upper}개 / 급등주: {max_surge}개)")
    print(f"============================================================")

    # 1. 데이터 수집
    stocks_df = get_stock_list('KRX')
    ohlcv_dict = get_all_ohlcv_cached(stocks_df, target_date=target_date, count=320)

    target_ts = pd.to_datetime(target_date)
    news_parser = NewsMomentumParser()

    upper_limit_candidates = []
    surge_candidates = []

    print(f"📊 {len(ohlcv_dict)}개 종목 대상 상한가/급등주 필터링 중...")

    for code, df in ohlcv_dict.items():
        if df.empty or target_ts not in df.index:
            continue

        df_slice = df.loc[:target_ts]
        if len(df_slice) < 5:
            continue

        latest = df_slice.iloc[-1]
        prev = df_slice.iloc[-2]

        close_price = float(latest['Close'])
        prev_close = float(prev['Close'])
        volume = float(latest['Volume'])
        amount = float(latest.get('Amount', close_price * volume))
        change_rate = round(((close_price - prev_close) / prev_close) * 100, 2)

        name_series = stocks_df[stocks_df['Code'] == code]['Name'].values
        name = name_series[0] if len(name_series) > 0 else code

        item_info = {
            "code": code,
            "name": name,
            "close": int(close_price),
            "prev_close": int(prev_close),
            "change_rate": change_rate,
            "amount": int(amount),
            "volume": int(volume),
            "df_slice": df_slice
        }

        # 조건 A: 상한가/하한가 (등락률 >= +29.5% 또는 <= -29.5%)
        if change_rate >= 29.5 or change_rate <= -29.5:
            upper_limit_candidates.append(item_info)

        # 조건 B: 거래대금 150억 이상 & +15.0% 이상 급등
        elif amount >= 15_000_000_000 and change_rate >= 15.0:
            surge_candidates.append(item_info)

    # 정렬 및 개수 제한 적용
    upper_limit_candidates.sort(key=lambda x: x['amount'], reverse=True)
    surge_candidates.sort(key=lambda x: x['amount'], reverse=True)

    selected_upper = upper_limit_candidates[:max_upper]
    selected_surge = surge_candidates[:max_surge]

    print(f"✅ 필터링 완수: 상한가/하한가 {len(selected_upper)}개 (최대 {max_upper}개) / 150억+15%+ 급등주 {len(selected_surge)}개 (최대 {max_surge}개)")

    # 2. 뉴스 파싱 (원문 링크 & 과거 히스토리 역추적) & 차트 생성
    for item in selected_upper + selected_surge:
        realtime_news = news_parser.fetch_stock_realtime_news(item['name'], item['code'])
        history_logs = news_parser.search_past_report_history(item['name'], item['code'])
        
        item['news_title'] = realtime_news.get('title', f"{item['name']} 당일 급등 이슈")
        item['news_link'] = realtime_news.get('link', '#')
        item['history_logs'] = history_logs
        item['chart_path'] = generate_surge_chart(item['df_slice'], item['code'], item['name'], target_date)

    # 3. 리포트 조립 (MD & HTML)
    scr_name = f"{target_date}_스크리닝"
    surge_name = f"{target_date}_당일상한가급등"

    # Markdown 빌드
    md_content = f"# 🔥 [당일 상한가/급등주 분석] {target_date} 시장 주도주 리포트\n\n"
    md_content += f"> 기준일: {target_date} | [📈 매매전 스크리닝 보고서 보기](./{scr_name}.html)\n\n---\n\n"

    md_content += f"## 🏆 1. 당일 상한가/하한가 달성 종목 (상위 {len(selected_upper)}개)\n\n"
    if selected_upper:
        for i, item in enumerate(selected_upper, 1):
            md_content += f"#### {i}) {item['name']} ({item['code']}) — <span style='color:#ef4444'><b>{item['change_rate']:+.2f}%</b></span>\n"
            md_content += f'<p align="center"><img src="{item["chart_path"]}" width="65%" alt="{item["name"]} 차트"/></p>\n\n'
            md_content += f"- **종가**: {item['close']:,}원 | **거래대금**: {fmt_amt(item['amount'])}\n"
            md_content += f"- **🔥 당일 핵심 뉴스**: 🔗 [{item['news_title']}]({item['news_link']})\n"
            if item['history_logs']:
                hist_str = ", ".join(item['history_logs'])
                md_content += f"- **📜 과거 부각 이력**: {hist_str}\n"
            md_content += "\n"
    else:
        md_content += "당일 상한가/하한가 포착 종목 없음\n\n"

    md_content += f"---\n\n## 🚀 2. 거래대금 150억+ & +15% 이상 폭등주 (상위 {len(selected_surge)}개)\n\n"
    if selected_surge:
        for i, item in enumerate(selected_surge, 1):
            md_content += f"#### {i}) {item['name']} ({item['code']}) — <span style='color:#ef4444'><b>{item['change_rate']:+.2f}%</b></span>\n"
            md_content += f'<p align="center"><img src="{item["chart_path"]}" width="65%" alt="{item["name"]} 차트"/></p>\n\n'
            md_content += f"- **종가**: {item['close']:,}원 | **거래대금**: {fmt_amt(item['amount'])}\n"
            md_content += f"- **🔥 당일 핵심 뉴스**: 🔗 [{item['news_title']}]({item['news_link']})\n"
            if item['history_logs']:
                hist_str = ", ".join(item['history_logs'])
                md_content += f"- **📜 과거 부각 이력**: {hist_str}\n"
            md_content += "\n"
    else:
        md_content += "조건 충족 급등주 포착 종목 없음\n\n"

    with open(REPORTS_DIR / f"{surge_name}.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    # HTML 빌드
    html_content = render_surge_html(selected_upper, selected_surge, target_date, scr_name, surge_name)
    with open(REPORTS_DIR / f"{surge_name}.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ 리포트 생성 완수: {surge_name}.md & {surge_name}.html")

    # 4. 대시보드 인덱서 재빌드
    print(f"🌐 대시보드 인덱서(generate_index.py) 재빌드 중...")
    try:
        if (REPO_DIR / "generate_index.py").exists():
            subprocess.run("python3 generate_index.py", cwd=str(REPO_DIR), shell=True, check=True)
            if (REPO_DIR / "index.html").exists():
                subprocess.run(["cp", str(REPO_DIR / "index.html"), str(BASE_DIR / "index.html")], check=False)
            print(f"✅ index.html 대시보드 성공적으로 재빌드 되었습니다!")
    except Exception as e:
        print(f"⚠️ 대시보드 재빌드 경고: {e}")

    # 5. 텔레그램 알림 발송
    from telegram_bot import TelegramBot
    bot = TelegramBot()
    if bot.chat_id:
        tg_msg = f"<b>🔥 [당일 상한가/급등주 분석] {target_date} 시장 주도주 리포트</b>\n"
        tg_msg += f"• 분석 기준일: {target_date}\n"
        tg_msg += f"• 상한가: {len(selected_upper)}개 / 150억+15%+ 급등: {len(selected_surge)}개\n"
        tg_msg += f"----------------------------------------\n\n"

        if selected_upper:
            tg_msg += "<b>🔴 [상한가/하한가 (Top 5)]</b>\n"
            for item in selected_upper[:5]:
                tg_msg += f"• <b>{item['name']}</b> ({item['change_rate']:+.2f}%) | {item['close']:,}원 ({fmt_amt(item['amount'])})\n"
            tg_msg += "\n"

        if selected_surge:
            tg_msg += "<b>🚀 [150억+ & +15%+ 급등주 (Top 10)]</b>\n"
            for item in selected_surge[:10]:
                tg_msg += f"• <b>{item['name']}</b> ({item['change_rate']:+.2f}%) | {item['close']:,}원 ({fmt_amt(item['amount'])})\n"

        bot.send_message(tg_msg)

    # 6. Git Push 배포
    print(f"🌐 GitHub 저장소 동기화 중...")
    try:
        subprocess.run(["cp", str(REPORTS_DIR / f"{surge_name}.html"), str(REPO_DIR / "reports" / f"{surge_name}.html")], check=False)
        subprocess.run(["cp", str(REPORTS_DIR / f"{surge_name}.md"), str(REPO_DIR / "reports" / f"{surge_name}.md")], check=False)
        subprocess.run(["cp", str(BASE_DIR / "index.html"), str(REPO_DIR / "index.html")], check=False)

        git_cmd = f"cd {REPO_DIR} && git add -A && git commit -m 'feat: {target_date} 당일 상한가(5개) 및 급등주(10개) 뉴스링크/히스토리 리포트 배포' && git push origin main"
        subprocess.run(git_cmd, shell=True, check=False)
        print(f"🎉 [Git Push 완수] {surge_name}.html 배포 완료!")
    except Exception as e:
        print(f"⚠️ Git Push 경고: {e}")


def render_surge_html(upper_list, surge_list, target_date, scr_name, surge_name):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_count = len(upper_list) + len(surge_list)

    cards_html = ""

    def render_section_cards(items, title, icon, color):
        nonlocal cards_html
        cards_html += f"""
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">{icon} {title}</h2>
            <div class="section-count">{len(items)}개 종목</div>
          </div>
          <div class="stock-grid">
        """
        if not items:
            cards_html += f'<div style="grid-column: 1/-1; padding: 2rem; text-align: center; color: var(--muted); background: var(--card-bg); border-radius: 16px;">포착된 종목이 없습니다.</div>'
        else:
            for item in items:
                badge_cls = "tag-top1" if item['change_rate'] >= 25.0 else "tag-sub"
                badge_txt = "🔥 상한가" if item['change_rate'] >= 29.5 else "🚀 폭등주"
                
                news_html = f'<a href="{item["news_link"]}" target="_blank" style="color:#60a5fa; font-weight:600; text-decoration:none;">🔗 {item["news_title"]} &rarr;</a>'
                
                history_html = ""
                if item.get('history_logs'):
                    hist_items = "".join([f'<span style="background:rgba(255,255,255,0.06); padding:0.15rem 0.5rem; border-radius:4px; font-size:0.78rem; margin-right:0.3rem;">📜 {h}</span>' for h in item['history_logs']])
                    history_html = f'<div style="margin-top:0.5rem;">{hist_items}</div>'

                cards_html += f"""
            <div class="stock-card">
              <div class="stock-header">
                <div class="stock-name-box">
                  <span class="stock-name">{item['name']}</span>
                  <span class="stock-code">{item['code']}</span>
                  <span class="tag-badge {badge_cls}">{badge_txt}</span>
                </div>
                <div style="font-size:1.1rem; font-weight:700; color:{color}">{item['change_rate']:+.2f}%</div>
              </div>
              <div class="stock-body">
                <div class="chart-container">
                  <img src="{item['chart_path']}" alt="{item['name']} 차트" class="chart-img">
                </div>
                <div class="info-panel">
                  <div class="metrics-row">
                    <div class="metric-box"><div class="metric-val">{item['close']:,}원</div><div class="metric-lbl">종가</div></div>
                    <div class="metric-box"><div class="metric-val" style="color:#ef4444">{fmt_amt(item['amount'])}</div><div class="metric-lbl">거래대금</div></div>
                    <div class="metric-box"><div class="metric-val" style="color:{color}">{item['change_rate']:+.2f}%</div><div class="metric-lbl">등락률</div></div>
                  </div>
                  <div class="opinion-box">
                    <strong>💡 당일 핵심 뉴스 & 모멘텀:</strong><br>{news_html}
                    {history_html}
                  </div>
                </div>
              </div>
            </div>
            """
        cards_html += "</div></div>"

    render_section_cards(upper_list, f"당일 상한가/하한가 달성 종목 (Top {len(upper_list)})", "🔴", "#ef4444")
    render_section_cards(surge_list, f"거래대금 150억+ & +15% 이상 폭등주 (Top {len(surge_list)})", "🚀", "#f43f5e")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔥 {target_date} 당일 상한가/급등주 분석 보고서</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #0b0f19;
  --card-bg: rgba(22, 28, 45, 0.75);
  --card-border: rgba(255, 255, 255, 0.08);
  --primary: #f43f5e;
  --text: #f3f4f6;
  --muted: #9ca3af;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh;
  background-image: radial-gradient(circle at 15% 15%, rgba(244, 63, 94, 0.15) 0%, transparent 45%), radial-gradient(circle at 85% 85%, rgba(168, 85, 247, 0.12) 0%, transparent 45%);
  background-attachment: fixed; padding-bottom: 5rem;
}}
header {{ text-align: center; padding: 3.5rem 1.5rem 2rem; }}
.badge-main {{ display: inline-block; background: linear-gradient(135deg, #f43f5e, #a855f7); color: #fff; padding: 0.4rem 1.2rem; border-radius: 50px; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 1rem; }}
h1 {{ font-family: 'Outfit', sans-serif; font-size: 2.5rem; font-weight: 800; background: linear-gradient(to right, #ffffff, #fca5a5, #f43f5e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.6rem; }}
.subtitle {{ color: var(--muted); font-size: 1rem; margin-bottom: 0.4rem; }}
container {{ max-width: 1150px; margin: 0 auto; padding: 0 1.5rem; display: block; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 2rem 0; }}
.stat-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.2rem; text-align: center; backdrop-filter: blur(12px); }}
.stat-num {{ font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #f43f5e; }}
.stat-label {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.2rem; }}
.section {{ margin-bottom: 3.5rem; }}
.section-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.8rem; }}
.section-title {{ font-family: 'Outfit', sans-serif; font-size: 1.5rem; font-weight: 700; display: flex; align-items: center; gap: 0.6rem; }}
.section-count {{ background: rgba(255, 255, 255, 0.06); padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; color: var(--muted); }}
.stock-grid {{ display: grid; grid-template-columns: 1fr; gap: 1.5rem; }}
.stock-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 20px; overflow: hidden; backdrop-filter: blur(12px); transition: transform 0.2s, border-color 0.2s; }}
.stock-card:hover {{ transform: translateY(-3px); border-color: rgba(244, 63, 94, 0.4); }}
.stock-header {{ padding: 1.2rem 1.5rem; background: rgba(255, 255, 255, 0.02); border-bottom: 1px solid var(--card-border); display: flex; align-items: center; justify-content: space-between; }}
.stock-name-box {{ display: flex; align-items: center; gap: 0.8rem; }}
.stock-name {{ font-size: 1.25rem; font-weight: 700; color: #fff; }}
.stock-code {{ font-size: 0.85rem; color: var(--muted); background: rgba(255, 255, 255, 0.05); padding: 0.2rem 0.5rem; border-radius: 6px; }}
.tag-badge {{ font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 50px; }}
.tag-top1 {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
.tag-sub {{ background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); }}
.stock-body {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 1.5rem; padding: 1.5rem; }}
@media (max-width: 850px) {{ .stock-body {{ grid-template-columns: 1fr; }} }}
.chart-container {{ border-radius: 12px; overflow: hidden; border: 1px solid var(--card-border); background: #000; }}
.chart-img {{ width: 100%; height: auto; display: block; }}
.info-panel {{ display: flex; flex-direction: column; gap: 1rem; justify-content: center; }}
.metrics-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; }}
.metric-box {{ background: rgba(0, 0, 0, 0.2); border: 1px solid var(--card-border); border-radius: 10px; padding: 0.6rem; text-align: center; }}
.metric-val {{ font-size: 0.95rem; font-weight: 700; margin-bottom: 0.1rem; }}
.metric-lbl {{ font-size: 0.75rem; color: var(--muted); }}
.opinion-box {{ background: rgba(244, 63, 94, 0.06); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 12px; padding: 1rem; font-size: 0.88rem; line-height: 1.5; color: #e5e7eb; }}
footer {{ text-align: center; color: var(--muted); font-size: 0.85rem; margin-top: 4rem; padding: 2rem; border-top: 1px solid var(--card-border); }}
</style>
</head>
<body>

<header>
  <div class="badge-main">실전플랜 1 · 당일 상한가/급등주 리포트</div>
  <h1>🔥 {target_date} 시장 주도주 분석</h1>
  <div class="subtitle">당일 상한가 및 거래대금 150억+ & +15% 이상 폭등주 분석 카드</div>
  <div><a href="{scr_name}.html" style="display:inline-flex; align-items:center; gap:0.4rem; background:rgba(99, 102, 241, 0.2); border:1px solid rgba(99, 102, 241, 0.4); color:#a5b4fc; text-decoration:none; padding:0.4rem 1rem; border-radius:50px; font-size:0.85rem; font-weight:700; margin-top:0.8rem;">📈 매매전 스크리닝 보고서 보기 &rarr;</a></div>
</header>

<container>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-num">{total_count}개</div>
      <div class="stat-label">총 주도주 포착 종목</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">{len(upper_list)}개</div>
      <div class="stat-label">상한가/하한가 달성 종목</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">{len(surge_list)}개</div>
      <div class="stat-label">150억+ & +15%+ 폭등주</div>
    </div>
  </div>

  {cards_html}
</container>

<footer>
  실전플랜 1 · 당일 상한가/급등주 보고서 · 생성일시: {now_str} · 리포트 시스템
</footer>

</body>
</html>
"""


if __name__ == "__main__":
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="당일 상한가 및 급등주 분석 리포트 실행기")
    parser.add_argument("--date", type=str, default=today_str, help="분석 대상일 (YYYY-MM-DD)")
    parser.add_argument("--max-upper", type=int, default=5, help="상한가/하한가 최대 포착 수")
    parser.add_argument("--max-surge", type=int, default=10, help="150억+15%+ 급등주 최대 포착 수")
    args = parser.parse_args()

    run_daily_surge_pipeline(target_date=args.date, max_upper=args.max_upper, max_surge=args.max_surge)

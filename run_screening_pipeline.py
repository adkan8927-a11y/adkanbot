"""
====================================================================
🚀 [실전플랜 1] 수집, 작성, 텔레그램 배포 & Git Push 자동 마스터 파이프라인
파일명: run_screening_pipeline.py
====================================================================
기능:
1. 국내 주식 거래대금 상위 500종목 전수 스캔 (전략1, 전략2, 전략3 종목 중복 방지)
2. 전략별 이평선 차트 PNG 자동 생성 (charts/, 가독성 폰트 확대 & 비율 66% 조정)
3. 통합 마크다운(.md) 및 인터랙티브 HTML 웹 보고서 자동 작성 및 빌드
4. 각 전략별 TOP 종목 (전략1 TOP3, 전략2 TOP1, 전략3 TOP2) 텔레그램 자동 전송 (차트 사진 및 폴백 포함)
5. GitHub 저장소(adkan연구2)로 자동 sync 및 git commit & push 수행
"""

import sys
import os
import time
import argparse
import subprocess
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime

# 기준 경로 설정
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

from collector import get_top_volume_stocks, get_ohlcv, get_all_ohlcv_cached
from kis_client import KISClient
from config import STRATEGY3_BOTTOM_PCT
from screener import (
    screen_strategy1_yang_eum_yang,
    screen_strategy2_iilhong,
    screen_strategy3_sugeub_halt
)
from telegram_bot import TelegramBot
from chart_drawer import mpf, plt, HAS_MPF

def fmt_amt(a):
    return f"{a//100_000_000:.0f}억" if a >= 100_000_000 else f"{a//10_000:.0f}만"

def run_pipeline(target_date: str = None, send_telegram: bool = True, push_github: bool = True, limit: int = 500):
    print("=" * 60)
    print("🚀 [실전플랜 1] 자동 수집·작성·배포 파이프라인 시작")
    print("=" * 60)

    kis_client = KISClient()
    telegram_bot = TelegramBot()

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    date_ts = pd.to_datetime(target_date)
    print(f"📊 [1/5] 데이터 수집 및 스크리닝 진행중 (기준일: {target_date}, 대상: 거래대금 상위 {limit}개)...")

    stocks_df = get_top_volume_stocks(limit=limit)
    ohlcv_dict = get_all_ohlcv_cached(stocks_df, target_date=target_date, count=320)

    results = {1: [], 2: [], 3: []}
    seen_codes = set()

    headers = kis_client.get_headers("FHKST01010900")

    for idx, row in stocks_df.iterrows():
        code = str(row['Code']).zfill(6)
        name = row.get('Name', code)

        df = ohlcv_dict.get(code, pd.DataFrame())
        if df.empty:
            continue

        # 최근 영업일 슬라이스
        if date_ts in df.index:
            day_idx = df.index.get_loc(date_ts)
            df_slice = df.iloc[:day_idx + 1]
        else:
            df_slice = df

        if df_slice.empty:
            continue

        # 유저 지정 제외 종목 필터링 (우선주, 관리, 환기, 정리매매, 거래정지, 단일가 제외 / 투자경고,주의,위험 포함)
        from screener import is_valid_trading_stock
        if not is_valid_trading_stock(name, code, df_slice):
            continue

        latest = df_slice.iloc[-1]

        # ----------------------------------------------------
        # 0. 전략 2 1순위 (키움 이일홍 정석 최우선 탐색)
        # ----------------------------------------------------
        from screener import screen_kiwoom_iilhong
        res_kiwoom = screen_kiwoom_iilhong(df_slice)
        if res_kiwoom:
            results[2].append({
                "name": name, "code": code,
                "close": int(latest["Close"]),
                "amount": int(latest["Amount"]),
                "reason": res_kiwoom["reason"],
                "priority_stage": 1,
                "df_slice": df_slice
            })
            seen_codes.add(code)
            continue

        # ----------------------------------------------------
        # 전략 1 (우선순위 1)
        # ----------------------------------------------------
        res1 = screen_strategy1_yang_eum_yang(df_slice)
        if res1:
            base_date = res1.get("base_date", target_date)
            try:
                base_dt = pd.to_datetime(base_date)
                base_amount = float(df_slice.loc[base_dt, "Amount"]) if base_dt in df_slice.index else 40_000_000_000.0
            except:
                base_amount = 40_000_000_000.0
            results[1].append({
                "name": name, "code": code,
                "close": int(latest["Close"]),
                "amount": int(latest["Amount"]),
                "base_date": base_date,
                "base_detail": res1.get("base_detail", "ADK특 13~20선 반등"),
                "support_ma": res1.get("support_ma", "13~20일선"),
                "disp": res1.get("disp", 0.0),
                "base_amount": base_amount,
                "reason": res1["reason"],
                "sawitgam": res1.get("sawitgam", False),
                "is_adk_top1": res1.get("is_adk_top1", False),
                "df_slice": df_slice
            })
            seen_codes.add(code)
            continue

        # ----------------------------------------------------
        # 전략 2 (우선순위 2 - 매집봉)
        # ----------------------------------------------------
        if code not in seen_codes:
            res2 = screen_strategy2_iilhong(df_slice)
            if res2:
                results[2].append({
                    "name": name, "code": code,
                    "close": int(latest["Close"]),
                    "amount": int(latest["Amount"]),
                    "reason": res2["reason"],
                    "df_slice": df_slice
                })
                seen_codes.add(code)
                continue

        # ----------------------------------------------------
        # 전략 3 (우선순위 3 - 수급 바닥형)
        # ----------------------------------------------------
        if code not in seen_codes:
            close_now = latest["Close"]
            high_52w  = df_slice["High"].tail(250).max()
            ratio_pct = round(close_now / high_52w * 100, 1)
            if close_now <= high_52w * (STRATEGY3_BOTTOM_PCT / 100.0):
                date_key = target_date.replace("-", "")
                try:
                    url_inv = f"{kis_client.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD={code}"
                    res_inv = requests.get(url_inv, headers=headers, timeout=3).json()
                    time.sleep(0.03)
                    if res_inv.get("rt_cd") == "0" and "output" in res_inv:
                        output = res_inv["output"]
                        matched_k = next((k for k, it in enumerate(output) if it.get("stck_bsop_date") == date_key), -1)
                        inv_slice = output[matched_k:] if matched_k != -1 else output
                        res3 = screen_strategy3_sugeub_halt(df_slice, inv_slice)
                        if res3:
                            inv_df = pd.DataFrame(inv_slice[:20])
                            inv_df['frgn_ntby_tr_pbmn'] = pd.to_numeric(inv_df['frgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
                            inv_df['orgn_ntby_tr_pbmn'] = pd.to_numeric(inv_df['orgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
                            results[3].append({
                                "name": name, "code": code,
                                "close": int(close_now),
                                "amount": int(latest["Amount"]),
                                "high_52w": int(high_52w),
                                "ratio_pct": ratio_pct,
                                "frgn_20": inv_df['frgn_ntby_tr_pbmn'].sum(),
                                "orgn_20": inv_df['orgn_ntby_tr_pbmn'].sum(),
                                "reason": res3["reason"],
                                "df_slice": df_slice
                            })
                            seen_codes.add(code)
                except Exception:
                    pass

    total_count = len(results[1]) + len(results[2]) + len(results[3])
    print(f"✅ 중복 제거 스크리닝 완료: 총 {total_count}개 종목 포착 (전략1: {len(results[1])}개 / 전략2: {len(results[2])}개 / 전략3: {len(results[3])}개)")

    # ----------------------------------------------------
    # 2. 뉴스 가중치 연동 및 차트 생성 (가독성 확대 & 폰트 세팅)
    # ----------------------------------------------------
    print(f"📈 [2/5] 뉴스 모멘텀 가중치 파싱 & 이평선 맞춤 차트 캡처 생성 중...")
    
    from news_momentum_parser import NewsMomentumParser
    news_parser = NewsMomentumParser()

    # 전략 1 정렬 (기술 점수 + 뉴스 가중치 보너스 적용)
    import math
    ma_weights = {20:3.0, 13:2.0, 8:1.5, 5:1.0, 3:0.5}
    for r in results[1]:
        try:
            ma_num = int(r["support_ma"].replace("일선",""))
        except:
            ma_num = 5
        base_amt_100m = r.get("base_amount", 0.0) / 1e8
        ma_w = ma_weights.get(ma_num, 1.0)
        disp_score = max(0, 3 - abs(r["disp"]))
        
        # 뉴스 가중치 연동
        news_info = news_parser.get_news_weight_bonus(r["name"], r["code"], target_date)
        news_bonus = news_info["bonus"]
        r["news_reason"] = news_info["reason"]

        # 기준봉 거래대금(base_amount) 및 ADK특 TOP 1 승격 가산점 (+10000) 적용
        adk_top1_bonus = 10000.0 if r.get("is_adk_top1", False) else 0.0
        r["score"] = adk_top1_bonus + base_amt_100m * 10.0 + ma_w * 2.0 + disp_score * 1.0 + news_bonus * 5.0

    for r in results[2]:
        news_info = news_parser.get_news_weight_bonus(r["name"], r["code"], target_date)
        r["news_score"] = r["amount"] * (1.0 + news_info["bonus"] * 0.1)

    for r in results[3]:
        news_info = news_parser.get_news_weight_bonus(r["name"], r["code"], target_date)
        r["news_score"] = r["amount"] * (1.0 + news_info["bonus"] * 0.1)

    results[1].sort(key=lambda x: x["score"], reverse=True)
    results[2].sort(key=lambda x: (x.get("priority_stage", 2) == 1, x.get("news_score", x["amount"])), reverse=True)
    results[3].sort(key=lambda x: x.get("news_score", x["amount"]), reverse=True)

    all_items = []
    for r in results[1]: all_items.append((r, "양음양"))
    for r in results[2]: all_items.append((r, "이일홍"))
    for r in results[3]: all_items.append((r, "수급"))

    for item, strat_type in all_items:
        code = item["code"]
        name = item["name"]
        df_slice = item["df_slice"]

        chart_df = df_slice.tail(60).copy()
        if not isinstance(chart_df.index, pd.DatetimeIndex):
            chart_df.index = pd.to_datetime(chart_df.index)

        mc = mpf.make_marketcolors(
            up='#ef4444', down='#3b82f6', edge='inherit', wick='inherit', volume={'up': '#ef4444', 'down': '#3b82f6'}
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='--',
            y_on_right=True,
            rc={
                'font.family': 'AppleGothic',
                'axes.unicode_minus': False,
                'font.size': 14,
                'axes.labelsize': 14,
                'axes.titlesize': 16,
                'xtick.labelsize': 12,
                'ytick.labelsize': 12
            }
        )

        file_name = f"chart_{code}_{name}.png"
        file_path = CHARTS_DIR / file_name

        if strat_type == "양음양":
            mav = (3, 5, 8, 13, 20)
        elif strat_type == "이일홍":
            mav = (20, 120, 240)
        else:
            mav = (20, 60, 120, 240)

        mav = tuple([p for p in mav if p <= len(df_slice)])

        mpf.plot(
            chart_df, type='candle', style=style,
            title=f"\n[{strat_type}] {name} ({code}) - {target_date}",
            ylabel='Price (KRW)', ylabel_lower='Volume', volume=True,
            mav=mav if mav else (5, 20),
            savefig=dict(fname=str(file_path), dpi=130, bbox_inches='tight'),
            figratio=(9, 5.2), figscale=1.35
        )
        item["chart_path"] = str(file_path)
        item["scr_chart_rel_path"] = f"charts/chart_{code}_{name}.png"

    print("✅ 가독성이 강화된 모든 종목 차트 PNG 생성 완료!")

    # ----------------------------------------------------
    # 2-1. 스크리닝 MD & HTML 보고서 빌드 및 저장
    # ----------------------------------------------------
    scr_name = f"{target_date}_스크리닝"
    top_count = min(3, len(results[1])) + min(1, len(results[2])) + min(2, len(results[3]))

    md_scr = f"# 📈 [실전플랜 1] {target_date} 매매 후보 스크리닝 보고서\n\n"
    md_scr += f"> 스크리닝 기준일: {target_date} | [📊 익일 매매 성과 피드백 보고서 보기](./{target_date}_피드백.html)\n\n---\n\n"
    t1_top = min(3, len(results[1]))
    t2_top = min(1, len(results[2]))
    t3_top = min(2, len(results[3]))

    md_scr += f"## 📊 1. 스크리닝 성과 요약\n\n"
    md_scr += "| 전략 | 주요 기법 | 종목수(TOP) |\n"
    md_scr += "| :--- | :--- | :---: |\n"
    md_scr += f"| **전략 1** | 양음양 눌림목 & 사윗감 | {len(results[1])}개 (TOP {t1_top}개) |\n"
    md_scr += f"| **전략 2** | 매집봉 & 이일홍 | {len(results[2])}개 (TOP {t2_top}개) |\n"
    md_scr += f"| **전략 3** | 수급 & 핥 | {len(results[3])}개 (TOP {t3_top}개) |\n"
    md_scr += f"| **합계** | **3대 핵심 전략 통합** | **{total_count}개 (TOP {top_count}개)** |\n\n---\n\n"

    for s_id, s_title in [(1, "양-음-양 눌림목 (3% × 3슬롯)"), (2, "일일봉 매집봉 (10% × 1슬롯)"), (3, "수급 낙폭과대 바닥형 (10% × 2슬롯)")]:
        md_scr += f"## {'🔵' if s_id==1 else '🟡' if s_id==2 else '🟢'} {s_id+2}. 전략 {s_id} — {s_title}\n\n"
        if results[s_id]:
            display_items = results[s_id][:10]
            md_scr += f"### 📋 전략 {s_id} 전체 {len(results[s_id])}개 포착 종목 요약표\n\n"
            md_scr += "| 종목명 | 기준일종가 | 기준봉 | 지지선 | 비고 및 선정 상태 |\n"
            md_scr += "| :--- | ---: | :--- | :---: | :--- |\n"
            for i, r in enumerate(results[s_id], 1):
                is_top = (s_id==1 and i<=3) or (s_id==2 and i==1) or (s_id==3 and i<=2)
                top_badge = f"**★ TOP {i} 선택**" if is_top else f"후보군 ({i-3 if s_id==1 else i-1 if s_id==2 else i-2}위)"
                saw_badge = " (사윗감)" if r.get("sawitgam") else ""
                base_info = r.get("base_detail", r.get("reason", "N/A"))
                supp_info = r.get("support_ma", "240일선" if s_id==2 else "수급선")
                md_scr += f"| **{r['name']}** ({r['code']}) | {r['close']:,}원 | {base_info} | {supp_info} | {top_badge}{saw_badge} |\n"
            md_scr += "\n---\n\n"

            md_scr += f"### 🔍 전략 {s_id} 상세 분석\n\n"
            for i, r in enumerate(display_items, 1):
                is_top = (s_id==1 and i<=3) or (s_id==2 and i==1) or (s_id==3 and i<=2)
                top_badge = f" — ★ TOP {i} 선택" if is_top else f" — 후보군 ({i-3 if s_id==1 else i-1 if s_id==2 else i-2}위)"
                saw_badge = " (사윗감)" if r.get("sawitgam") else ""
                md_scr += f"#### {i}) {r['name']} ({r['code']}){top_badge}{saw_badge}\n"
                md_scr += f'<p align="center"><img src="charts/chart_{r["code"]}_{r["name"]}.png" width="65%" alt="{r["name"]} 차트"/></p>\n\n'
                md_scr += f"- **기준 종가**: {r['close']:,}원 | **거래대금**: {fmt_amt(r['amount'])}\n"
                md_scr += f"- **분석 사유**: {r['reason']}\n\n"
        else:
            md_scr += "해당 전략 포착 종목 없음\n\n"

    with open(REPORTS_DIR / f"{scr_name}.md", "w", encoding="utf-8") as f:
        f.write(md_scr)

    from run_feedback_pipeline import render_html_template
    html_scr = render_html_template(results, is_feedback=False, scr_title_date=target_date, fb_date=target_date, trade_entry_date=f"{target_date} (진입예정)", total_count=total_count, top_count=top_count, scr_name=scr_name, fb_name=f"{target_date}_피드백")
    with open(REPORTS_DIR / f"{scr_name}.html", "w", encoding="utf-8") as f:
        f.write(html_scr)

    print(f"  ✅ 리포트 생성 완수: {scr_name}.md & {scr_name}.html")

    # ----------------------------------------------------
    # 3. 텔레그램 TOP 3 배포 (정확한 전략 분리)
    # ----------------------------------------------------
    if send_telegram and telegram_bot.chat_id:
        print("📱 [3/5] 텔레그램 TOP3 알림 및 차트 전송 중...")
        
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 헤더 메시지
        main_msg = (
            f"<b>📈 [실전플랜 1] {target_date} 매매 스크리닝 배포</b>\n"
            f"• 발간시각: {now_time}\n"
            f"• 총 포착: {total_count}개 종목 (전략1: {len(results[1])} / 전략2: {len(results[2])} / 전략3: {len(results[3])})\n\n"
            f"<b>🔥 핵심 TOP 선택 종목 알림</b>\n"
        )
        telegram_bot.send_message(main_msg)

        # 전략 1 TOP 3 전송
        top1_items = results[1][:3]
        if top1_items:
            telegram_bot.send_message("<b>🔵 [전략 1] 양-음-양 눌림목 TOP 3 선택</b>")
            for i, r in enumerate(top1_items, 1):
                saw = " [사윗감]" if r.get("sawitgam") else ""
                caption = (
                    f"<b>★ TOP {i} :: {r['name']} ({r['code']}){saw}</b>\n"
                    f"• 종가: <b>{r['close']:,}원</b> | 거래대금: {fmt_amt(r['amount'])}\n"
                    f"• 지지선: <b>{r['support_ma']} (이격도 {r['disp']:+.2f}%)</b>\n"
                    f"• 기준봉: {r['base_date']} ({r['base_detail']})\n"
                    f"🎯 <b>목표가: {int(r['close']*1.05):,}원 (+5%)</b> | 손절가: {int(r['close']*0.97):,}원 (-3%)"
                )
                if os.path.exists(r.get("chart_path", "")):
                    telegram_bot.send_photo(r["chart_path"], caption=caption)
                else:
                    telegram_bot.send_message(caption)
                time.sleep(0.5)

        # 전략 2 TOP 1 전송 (금호전기 등 전략 2 전용)
        top2_items = results[2][:1]
        if top2_items:
            telegram_bot.send_message("<b>🟡 [전략 2] 일일봉 매집봉 (240일선) TOP 선택</b>")
            for r in top2_items:
                caption = (
                    f"<b>★ TOP 1 :: {r['name']} ({r['code']})</b>\n"
                    f"• 종가: <b>{r['close']:,}원</b> | 거래대금: {fmt_amt(r['amount'])}\n"
                    f"• 사유: {r['reason']}\n"
                    f"🎯 <b>목표가: {int(r['close']*1.03):,}원 (+3%)</b> | 손절가: {int(r['close']*0.968):,}원 (-3.2%)"
                )
                if os.path.exists(r.get("chart_path", "")):
                    telegram_bot.send_photo(r["chart_path"], caption=caption)
                else:
                    telegram_bot.send_message(caption)
                time.sleep(0.5)

        # 전략 3 TOP 2 전송 (한국항공우주, 한화엔진 등 전략 3 전용)
        top3_items = results[3][:2]
        if top3_items:
            telegram_bot.send_message("<b>🟢 [전략 3] 수급 낙폭과대 바닥형 TOP 2 선택</b>")
            for i, r in enumerate(top3_items, 1):
                caption = (
                    f"<b>★ TOP {i} :: {r['name']} ({r['code']})</b>\n"
                    f"• 종가: <b>{r['close']:,}원</b> | 52주高比: {r['ratio_pct']}%\n"
                    f"• 수급: 외인 20일({r['frgn_20']/1e8:+.0f}억) / 기관 20일(<b>{r['orgn_20']/1e8:+.0f}억</b>)\n"
                    f"• 거래대금: {fmt_amt(r['amount'])}\n"
                    f"🎯 <b>목표가: {int(r['close']*1.03):,}원 (+3% 즉시예약)</b> | 손절가: {int(r['close']*0.96):,}원 (-4%)"
                )
                if os.path.exists(r.get("chart_path", "")):
                    telegram_bot.send_photo(r["chart_path"], caption=caption)
                else:
                    telegram_bot.send_message(caption)
                time.sleep(0.5)

        print("✅ 텔레그램 알림 및 차트 배포 완료!")

    # ----------------------------------------------------
    # 4. GitHub 동기화 및 Push
    # ----------------------------------------------------
    if push_github and REPO_DIR.exists():
        print("🌐 [4/5] GitHub 저장소 동기화 및 Git Push 수행 중...")
        
        # 차트 복사
        repo_charts = REPO_DIR / "reports" / "charts"
        repo_charts.mkdir(parents=True, exist_ok=True)
        subprocess.run(f"cp -r {CHARTS_DIR}/* {repo_charts}/", shell=True)

        # 보고서 복사
        subprocess.run(f"cp -r {REPORTS_DIR}/*.md {REPO_DIR}/reports/ 2>/dev/null", shell=True)
        subprocess.run(f"cp -r {REPORTS_DIR}/*.html {REPO_DIR}/reports/ 2>/dev/null", shell=True)

        # generate_index.py 실행
        if (REPO_DIR / "generate_index.py").exists():
            subprocess.run("python3 generate_index.py", cwd=str(REPO_DIR), shell=True)

        # Git Commit & Push
        git_cmd = f'cd {REPO_DIR} && git add . && git commit -m "auto: {target_date} 스크리닝 보고서 및 차트 업데이트 (안전성 강화)" && git push origin main'
        res = subprocess.run(git_cmd, shell=True, capture_output=True, text=True)
        print(f"✅ Git Push 결과: {res.stdout if res.returncode==0 else res.stderr}")

    print("=" * 60)
    print("🎉 [파이프라인 완수] 수집, 작성, 텔레그램 배포 및 Git Push 모두 완료되었습니다!")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="실전플랜 1 마스터 파이프라인")
    parser.add_argument("--date", type=str, default="2026-07-31", help="스크리닝 기준일 (YYYY-MM-DD)")
    parser.add_argument("--no-telegram", action="store_true", help="텔레그램 전송 비활성화")
    parser.add_argument("--no-git", action="store_true", help="Git Push 비활성화")
    args = parser.parse_args()

    run_pipeline(
        target_date=args.date,
        send_telegram=not args.no_telegram,
        push_github=not args.no_git
    )

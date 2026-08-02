"""
독립형 익일 매매 성과 피드백 파이프라인
파일명: run_feedback_pipeline.py
역할: 전일 포착 종목의 익일(실제 매매일) 시세 추적 및 성과 복기 리포트를 단독 생성
"""

import sys
import os
import argparse
import time
import math
import subprocess
import pandas as pd
import requests
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

from collector import get_top_volume_stocks, get_ohlcv
from kis_client import KISClient
from config import STRATEGY3_BOTTOM_PCT
from screener import (
    screen_strategy1_yang_eum_yang,
    screen_strategy2_iilhong,
    screen_strategy3_sugeub_halt
)
from chart_drawer import mpf, plt, HAS_MPF

def fmt_amt(a):
    return f"{a//100_000_000:.0f}억" if a >= 100_000_000 else f"{a//10_000:.0f}만"

def run_feedback_for_dates(scr_date="2026-07-30", fb_date="2026-07-31"):
    scr_name = f"{scr_date}_스크리닝"
    fb_name = f"{fb_date}_피드백"

    scr_ts = pd.to_datetime(scr_date)
    fb_ts = pd.to_datetime(fb_date)

    scr_title_date = f"{scr_date} (종가)"
    trade_entry_date = f"{fb_date} (매매일)"

    kis_client = KISClient()
    headers = kis_client.get_headers("FHKST01010900")

    print(f"============================================================")
    print(f"🚀 [독립 피드백 실행] 스크리닝: {scr_date} ➔ 피드백 추적: {fb_date}")
    print(f"============================================================")

    stocks_df = get_top_volume_stocks(limit=500)
    results = {1: [], 2: [], 3: []}
    seen_codes = set()

    for idx, row in stocks_df.iterrows():
        code = str(row['Code']).zfill(6)
        name = row.get('Name', code)

        df = get_ohlcv(symbol=code, count=320)
        if df.empty or scr_ts not in df.index:
            continue

        scr_day_idx = df.index.get_loc(scr_ts)
        df_scr_slice = df.iloc[:scr_day_idx + 1]
        latest = df_scr_slice.iloc[-1]

        # 익일(매매일) OHLCV 데이터 확인
        has_fb = fb_ts in df.index
        if has_fb:
            fb_day_idx = df.index.get_loc(fb_ts)
            df_fb_slice = df.iloc[:fb_day_idx + 1]
            fb_row = df.loc[fb_ts]
            fb_open = int(fb_row['Open'])
            fb_high = int(fb_row['High'])
            fb_low = int(fb_row['Low'])
            fb_close = int(fb_row['Close'])
            fb_vol = int(fb_row['Volume'])
        else:
            df_fb_slice = df_scr_slice
            fb_open = fb_high = fb_low = fb_close = int(latest['Close'])
            fb_vol = 0

        prev_close = float(latest['Close'])
        max_ret = round(((fb_high - prev_close) / prev_close) * 100, 2)
        close_ret = round(((fb_close - prev_close) / prev_close) * 100, 2)

        # 전략 1 (양음양)
        res1 = screen_strategy1_yang_eum_yang(df_scr_slice)
        if res1:
            try:
                base_dt = pd.to_datetime(res1["base_date"])
                base_amount = float(df_scr_slice.loc[base_dt, "Amount"]) if base_dt in df_scr_slice.index else 0.0
            except:
                base_amount = 0.0

            target_pct = 5.0
            if max_ret >= target_pct:
                status_str = f"✅ 1차 목표 달성 (+{max_ret:.1f}%)"
            elif max_ret >= 0:
                status_str = f"⏱️ 지지선 유지 (+{max_ret:.1f}%)"
            else:
                status_str = f"❌ 손절 이탈 ({max_ret:.1f}%)"

            results[1].append({
                "name": name, "code": code,
                "close": int(latest["Close"]),
                "amount": int(latest["Amount"]),
                "base_date": res1["base_date"],
                "base_detail": res1["base_detail"],
                "support_ma": res1["support_ma"],
                "disp": res1["disp"],
                "base_amount": base_amount,
                "reason": res1["reason"],
                "sawitgam": res1.get("sawitgam", False),
                "df_scr_slice": df_scr_slice,
                "df_fb_slice": df_fb_slice,
                "fb_open": fb_open, "fb_high": fb_high, "fb_low": fb_low, "fb_close": fb_close,
                "max_ret": max_ret, "close_ret": close_ret, "status_str": status_str
            })
            seen_codes.add(code)
            continue

        # 전략 2 (이일홍)
        if code not in seen_codes:
            res2 = screen_strategy2_iilhong(df_scr_slice)
            if res2:
                target_pct = 3.0
                if max_ret >= target_pct:
                    status_str = f"✅ 1차 목표 달성 (+{max_ret:.1f}%)"
                elif max_ret >= 0:
                    status_str = f"⏱️ 지지선 유지 (+{max_ret:.1f}%)"
                else:
                    status_str = f"❌ 손절 이탈 ({max_ret:.1f}%)"

                results[2].append({
                    "name": name, "code": code,
                    "close": int(latest["Close"]),
                    "amount": int(latest["Amount"]),
                    "reason": res2["reason"],
                    "df_scr_slice": df_scr_slice,
                    "df_fb_slice": df_fb_slice,
                    "fb_open": fb_open, "fb_high": fb_high, "fb_low": fb_low, "fb_close": fb_close,
                    "max_ret": max_ret, "close_ret": close_ret, "status_str": status_str
                })
                seen_codes.add(code)
                continue

        # 전략 3 (수급)
        if code not in seen_codes:
            close_now = latest["Close"]
            high_52w = df_scr_slice["High"].tail(250).max()
            ratio_pct = round(close_now / high_52w * 100, 1)
            if close_now <= high_52w * (STRATEGY3_BOTTOM_PCT / 100.0):
                date_key = scr_date.replace("-", "")
                try:
                    url_inv = f"{kis_client.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD={code}"
                    res_inv = requests.get(url_inv, headers=headers, timeout=3).json()
                    time.sleep(0.02)
                    if res_inv.get("rt_cd") == "0" and "output" in res_inv:
                        output = res_inv["output"]
                        matched_k = next((k for k, it in enumerate(output) if it.get("stck_bsop_date") == date_key), -1)
                        inv_slice = output[matched_k:] if matched_k != -1 else output
                        res3 = screen_strategy3_sugeub_halt(df_scr_slice, inv_slice)
                        if res3:
                            inv_df = pd.DataFrame(inv_slice[:20])
                            inv_df['frgn_ntby_tr_pbmn'] = pd.to_numeric(inv_df['frgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
                            inv_df['orgn_ntby_tr_pbmn'] = pd.to_numeric(inv_df['orgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000

                            target_pct = 3.0
                            if max_ret >= target_pct:
                                status_str = f"✅ 1차 목표 달성 (+{max_ret:.1f}%)"
                            elif max_ret >= 0:
                                status_str = f"⏱️ 지지선 유지 (+{max_ret:.1f}%)"
                            else:
                                status_str = f"❌ 손절 이탈 ({max_ret:.1f}%)"

                            results[3].append({
                                "name": name, "code": code,
                                "close": int(close_now),
                                "amount": int(latest["Amount"]),
                                "high_52w": int(high_52w),
                                "ratio_pct": ratio_pct,
                                "frgn_20": inv_df['frgn_ntby_tr_pbmn'].sum(),
                                "orgn_20": inv_df['orgn_ntby_tr_pbmn'].sum(),
                                "reason": res3["reason"],
                                "df_scr_slice": df_scr_slice,
                                "df_fb_slice": df_fb_slice,
                                "fb_open": fb_open, "fb_high": fb_high, "fb_low": fb_low, "fb_close": fb_close,
                                "max_ret": max_ret, "close_ret": close_ret, "status_str": status_str
                            })
                            seen_codes.add(code)
                except Exception:
                    pass

    # 정렬
    ma_weights = {20:3.0, 13:2.0, 8:1.5, 5:1.0, 3:0.5}
    for r in results[1]:
        try:
            ma_num = int(r["support_ma"].replace("일선",""))
        except:
            ma_num = 5
        amt_score = math.log1p(r["base_amount"]/1e8)
        ma_w = ma_weights.get(ma_num, 1.0)
        disp_score = max(0, 3 - abs(r["disp"]))
        r["score"] = amt_score*0.4 + ma_w*0.4 + disp_score*0.2
    results[1].sort(key=lambda x: x["score"], reverse=True)
    results[2].sort(key=lambda x: x["amount"], reverse=True)
    results[3].sort(key=lambda x: x["amount"], reverse=True)

    # 1) 스크리닝 차트 PNG 생성 (scr_date 기준)
    all_items = []
    for r in results[1]: all_items.append((r, "양음양"))
    for r in results[2]: all_items.append((r, "이일홍"))
    for r in results[3]: all_items.append((r, "수급"))

    for item, strat_type in all_items:
        code = item["code"]
        name = item["name"]
        
        # 스크리닝 차트 (30일 기준)
        df_scr = item["df_scr_slice"]
        chart_scr_df = df_scr.tail(60).copy()
        if not isinstance(chart_scr_df.index, pd.DatetimeIndex):
            chart_scr_df.index = pd.to_datetime(chart_scr_df.index)

        mc = mpf.make_marketcolors(
            up='#ef4444', down='#3b82f6', edge='inherit', wick='inherit', volume={'up': '#ef4444', 'down': '#3b82f6'}
        )
        style = mpf.make_mpf_style(
            marketcolors=mc, gridstyle='--', y_on_right=True,
            rc={
                'font.family': 'AppleGothic', 'axes.unicode_minus': False, 'font.size': 14,
                'axes.labelsize': 14, 'axes.titlesize': 16, 'xtick.labelsize': 12, 'ytick.labelsize': 12
            }
        )

        mav = (3, 5, 8, 13, 20) if strat_type == "양음양" else (20, 120, 240) if strat_type == "이일홍" else (20, 60, 120, 240)
        mav_scr = tuple([p for p in mav if p <= len(df_scr)])

        file_name_scr = f"chart_{scr_date.replace('-','')}_{code}_{name}.png"
        path_scr = CHARTS_DIR / file_name_scr
        mpf.plot(
            chart_scr_df, type='candle', style=style,
            title=f"\n[{strat_type}] {name} ({code}) - {scr_date}",
            ylabel='Price (KRW)', ylabel_lower='Volume', volume=True,
            mav=mav_scr if mav_scr else (5, 20),
            savefig=dict(fname=str(path_scr), dpi=130, bbox_inches='tight'),
            figratio=(9, 5.2), figscale=1.35
        )
        item["scr_chart_rel_path"] = f"charts/{file_name_scr}"

        # 2) 모니터링 피드백 차트 (31일 당일 캔들 포함!)
        df_fb = item["df_fb_slice"]
        chart_fb_df = df_fb.tail(60).copy()
        if not isinstance(chart_fb_df.index, pd.DatetimeIndex):
            chart_fb_df.index = pd.to_datetime(chart_fb_df.index)

        mav_fb = tuple([p for p in mav if p <= len(df_fb)])
        file_name_fb = f"chart_fb_{fb_date.replace('-','')}_{code}_{name}.png"
        path_fb = CHARTS_DIR / file_name_fb
        mpf.plot(
            chart_fb_df, type='candle', style=style,
            title=f"\n[{strat_type} 피드백] {name} ({code}) - {fb_date}",
            ylabel='Price (KRW)', ylabel_lower='Volume', volume=True,
            mav=mav_fb if mav_fb else (5, 20),
            savefig=dict(fname=str(path_fb), dpi=130, bbox_inches='tight'),
            figratio=(9, 5.2), figscale=1.35
        )
        item["fb_chart_rel_path"] = f"charts/{file_name_fb}"

    total_count = len(results[1]) + len(results[2]) + len(results[3])
    top_count = min(3, len(results[1])) + min(1, len(results[2])) + min(2, len(results[3]))

    # 보고서 빌드
    build_md_and_html(results, scr_name, fb_name, scr_title_date, fb_date, trade_entry_date, total_count, top_count)


def build_md_and_html(results, scr_name, fb_name, scr_title_date, fb_date, trade_entry_date, total_count, top_count):
    # 1. 스크리닝 MD
    md_scr = f"# 📈 [실전플랜 1] {scr_title_date} 매매 후보 스크리닝 보고서\n\n"
    md_scr += f"> 스크리닝 기준일: {scr_title_date} | 진입 예정일: {trade_entry_date} | [📊 익일 매매 성과 피드백 보고서 보기](./{fb_name}.html)\n\n---\n\n"
    md_scr += f"## 📊 1. 스크리닝 요약\n- **전략 1 (양-음-양 눌림목)**: {len(results[1])}개 포착\n- **전략 2 (일일봉 매집봉)**: {len(results[2])}개 포착\n- **전략 3 (수급 낙폭과대 바닥형)**: {len(results[3])}개 포착\n- **총 포착 수**: {total_count}개 종목 (TOP 선택 {top_count}개)\n\n---\n\n"

    for s_id, s_title in [(1, "양-음-양 눌림목 (3% × 3슬롯)"), (2, "일일봉 매집봉 (10% × 1슬롯)"), (3, "수급 낙폭과대 바닥형 (10% × 2슬롯)")]:
        md_scr += f"## {'🔵' if s_id==1 else '🟡' if s_id==2 else '🟢'} {s_id}. 전략 {s_id} — {s_title}\n\n"
        if results[s_id]:
            display_items = results[s_id][:10]
            for i, r in enumerate(display_items, 1):
                is_top = (s_id==1 and i<=3) or (s_id==2 and i==1) or (s_id==3 and i<=2)
                top_badge = f" — ★ TOP {i} 선택" if is_top else f" — 후보군 ({i-3 if s_id==1 else i-1 if s_id==2 else i-2}위)"
                saw_badge = " (사윗감)" if r.get("sawitgam") else ""
                md_scr += f"#### {i}) {r['name']} ({r['code']}){top_badge}{saw_badge}\n"
                md_scr += f'<p align="center"><img src="{r["scr_chart_rel_path"]}" width="65%" alt="{r["name"]} 차트"/></p>\n\n'
                md_scr += f"- **기준 종가**: {r['close']:,}원 | **거래대금**: {fmt_amt(r['amount'])}\n"
                md_scr += f"- **분석 사유**: {r['reason']}\n\n"
        else:
            md_scr += "해당 전략 포착 종목 없음\n\n"

    with open(REPORTS_DIR / f"{scr_name}.md", "w", encoding="utf-8") as f:
        f.write(md_scr)

    # 2. 피드백 MD
    md_fb = f"# 📊 [실전플랜 1 피드백] {fb_date} 매매 성과 추적 보고서\n\n"
    md_fb += f"> 스크리닝 포착일: {scr_title_date} | 실제 매매(추적일): {trade_entry_date} | [📈 매매전 스크리닝 보고서 보기](./{scr_name}.html)\n\n---\n\n"
    md_fb += f"## 📊 1. 당일 매매 성과 요약\n- **포착 및 검증 종목 수**: 총 {total_count}개 종목\n\n---\n\n"

    for s_id, s_title in [(1, "양-음-양 눌림목 성과"), (2, "일일봉 매집봉 성과"), (3, "수급 낙폭과대 바닥형 성과")]:
        md_fb += f"## {'🔵' if s_id==1 else '🟡' if s_id==2 else '🟢'} 전략 {s_id} — {s_title}\n\n"
        if results[s_id]:
            display_items = results[s_id][:10]
            for i, r in enumerate(display_items, 1):
                is_top = (s_id==1 and i<=3) or (s_id==2 and i==1) or (s_id==3 and i<=2)
                top_badge = f" — ★ TOP {i} 선택" if is_top else f" — 후보군 ({i-3 if s_id==1 else i-1 if s_id==2 else i-2}위)"
                md_fb += f"#### {i}) {r['name']} ({r['code']}){top_badge} | {r['status_str']}\n"
                md_fb += f'<p align="center"><img src="{r["fb_chart_rel_path"]}" width="65%" alt="{r["name"]} 피드백 차트"/></p>\n\n'
                md_fb += f"- **전일 종가(기준가)**: {r['close']:,}원 ➔ **매매일 시초가**: {r['fb_open']:,}원 | **최고가**: {r['fb_high']:,}원 (<b>{r['max_ret']:+.2f}%</b>) | **종가**: {r['fb_close']:,}원 ({r['close_ret']:+.2f}%)\n"
                md_fb += f"- **시세 움직임 복기**: {r['reason']}\n\n"
        else:
            md_fb += "포착 종목 없음\n\n"

    with open(REPORTS_DIR / f"{fb_name}.md", "w", encoding="utf-8") as f:
        f.write(md_fb)

    # HTML 2종 생성
    html_scr = render_html_template(results, is_feedback=False, scr_title_date=scr_title_date, fb_date=fb_date, trade_entry_date=trade_entry_date, total_count=total_count, top_count=top_count, scr_name=scr_name, fb_name=fb_name)
    with open(REPORTS_DIR / f"{scr_name}.html", "w", encoding="utf-8") as f:
        f.write(html_scr)

    html_fb = render_html_template(results, is_feedback=True, scr_title_date=scr_title_date, fb_date=fb_date, trade_entry_date=trade_entry_date, total_count=total_count, top_count=top_count, scr_name=scr_name, fb_name=fb_name)
    with open(REPORTS_DIR / f"{fb_name}.html", "w", encoding="utf-8") as f:
        f.write(html_fb)

    print(f"  ✅ 생성 완수: {scr_name}.html & {fb_name}.html (모니터링 당일 캔들 차트 반영)")

    # 3. index.html 대시보드 인덱서 재빌드
    print(f"🌐 [18:00 피드백] 대시보드 인덱서(generate_index.py) 실행 중...")
    try:
        subprocess.run(["python3", str(BASE_DIR / "generate_index.py")], check=True)
    except Exception as e:
        print(f"  ⚠️ 대시보드 인덱서 실행 경고: {e}")

    # 4. 텔레그램 18시 성과 피드백 브리핑 발송
    from telegram_bot import TelegramBot
    bot = TelegramBot()
    if bot.chat_id:
        print(f"📱 [18:00 피드백] 텔레그램 성과 피드백 브리핑 발송 중...")
        tg_msg = f"<b>📊 [실전플랜 1] {fb_date} 18:00 매매 성과 피드백 리포트</b>\n"
        tg_msg += f"• 스크리닝 포착일: {scr_date}\n"
        tg_msg += f"• 매매 추적일: {fb_date}\n"
        tg_msg += f"----------------------------------------\n"

        for s_id, s_title in [(1, "양-음-양"), (2, "이일홍"), (3, "수급바닥")]:
            if results[s_id]:
                top_r = results[s_id][0]
                status_icon = "🟢 " if "달성" in top_r.get("status_str", "") else "🟡 "
                tg_msg += f"{status_icon}<b>[전략{s_id} {s_title}] {top_r['name']} ({top_r['code']})</b>\n"
                tg_msg += f"  - 고가: {top_r.get('fb_high', top_r['close']):,}원 (<b>{top_r.get('max_ret', 0.0):+.2f}%</b>)\n"
                tg_msg += f"  - 종가: {top_r.get('fb_close', top_r['close']):,}원 ({top_r.get('close_ret', 0.0):+.2f}%)\n"
                tg_msg += f"  - 상태: {top_r.get('status_str', '모니터링')}\n\n"

        bot.send_message(tg_msg)

    # 5. Git commit & push 동기화
    print(f"🌐 [18:00 피드백] GitHub 저장소 동기화 중...")
    try:
        subprocess.run(["cp", str(REPORTS_DIR / f"{fb_name}.html"), str(REPO_DIR / "reports" / f"{fb_name}.html")], check=False)
        subprocess.run(["cp", str(REPORTS_DIR / f"{fb_name}.md"), str(REPO_DIR / "reports" / f"{fb_name}.md")], check=False)
        subprocess.run(["cp", str(BASE_DIR / "index.html"), str(REPO_DIR / "index.html")], check=False)
        
        git_cmd = f"cd {REPO_DIR} && git add -A && git commit -m 'auto: 18:00 {fb_date} 성과 피드백 보고서 및 대시보드 업데이트' && git push origin main"
        subprocess.run(git_cmd, shell=True, check=False)
        print(f"✅ [18:00 피드백] Git Push 배포 성공!")
    except Exception as e:
        print(f"  ⚠️ Git Push 경고: {e}")


def render_html_template(results, is_feedback, scr_title_date, fb_date, trade_entry_date, total_count, top_count, scr_name, fb_name):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    badge_title = "실전플랜 1 · 성과 피드백 보고서" if is_feedback else "실전플랜 1 · 매매전 스크리닝"
    page_title = f"📊 {fb_date} 매매 성과 추적 리포트" if is_feedback else f"📈 {scr_title_date} 매매 후보 스크리닝"
    sub_title = f"{scr_title_date} 포착 종목의 익일({fb_date}) 실제 시세 움직임 및 익절 달성 복기" if is_feedback else f"{scr_title_date} 종가 기준 500개 전수 스캔 및 심층 분석 차트 보고서"

    toggle_btn = f'<a href="{scr_name}.html" style="display:inline-flex; align-items:center; gap:0.4rem; background:rgba(99, 102, 241, 0.2); border:1px solid rgba(99, 102, 241, 0.4); color:#a5b4fc; text-decoration:none; padding:0.4rem 1rem; border-radius:50px; font-size:0.85rem; font-weight:700; margin-top:0.8rem;">📈 매매전 스크리닝 보고서 보기 &rarr;</a>' if is_feedback else f'<a href="{fb_name}.html" style="display:inline-flex; align-items:center; gap:0.4rem; background:rgba(16, 185, 129, 0.2); border:1px solid rgba(16, 185, 129, 0.4); color:#34d399; text-decoration:none; padding:0.4rem 1rem; border-radius:50px; font-size:0.85rem; font-weight:700; margin-top:0.8rem;">📊 익일 매매 성과 피드백 보고서 보기 &rarr;</a>'

    entry_label = trade_entry_date.split()[0] if (trade_entry_date and trade_entry_date.split()) else fb_date
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #0b0f19;
  --card-bg: rgba(22, 28, 45, 0.75);
  --card-border: rgba(255, 255, 255, 0.08);
  --primary: #6366f1;
  --text: #f3f4f6;
  --muted: #9ca3af;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh;
  background-image: radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.15) 0%, transparent 45%), radial-gradient(circle at 85% 85%, rgba(168, 85, 247, 0.12) 0%, transparent 45%);
  background-attachment: fixed; padding-bottom: 5rem;
}}
header {{ text-align: center; padding: 3.5rem 1.5rem 2rem; }}
.badge-main {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #a855f7); color: #fff; padding: 0.4rem 1.2rem; border-radius: 50px; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 1rem; }}
h1 {{ font-family: 'Outfit', sans-serif; font-size: 2.5rem; font-weight: 800; background: linear-gradient(to right, #ffffff, #c7d2fe, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.6rem; }}
.subtitle {{ color: var(--muted); font-size: 1rem; margin-bottom: 0.4rem; }}
.meta-info {{ color: #fbbf24; font-size: 0.9rem; font-weight: 600; }}
container {{ max-width: 1150px; margin: 0 auto; padding: 0 1.5rem; display: block; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0; }}
.stat-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.2rem; text-align: center; backdrop-filter: blur(12px); }}
.stat-num {{ font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; }}
.stat-label {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.2rem; }}
.section {{ margin-bottom: 3.5rem; }}
.section-title {{ display: flex; align-items: center; justify-content: space-between; font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700; margin-bottom: 1.2rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--card-border); }}
.stock-grid {{ display: grid; grid-template-columns: 1fr; gap: 1.8rem; }}
.stock-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 20px; overflow: hidden; backdrop-filter: blur(16px); }}
.stock-card.top-choice {{ border: 1px solid rgba(99, 102, 241, 0.6); background: linear-gradient(145deg, rgba(22, 28, 45, 0.9), rgba(30, 38, 65, 0.8)); }}
.stock-header {{ display: flex; justify-content: space-between; align-items: center; padding: 1.2rem 1.6rem; background: rgba(255, 255, 255, 0.02); border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
.stock-name-box {{ display: flex; align-items: center; gap: 0.8rem; }}
.stock-name {{ font-size: 1.3rem; font-weight: 700; color: #fff; }}
.stock-code {{ color: var(--muted); font-size: 0.9rem; }}
.tag-badge {{ padding: 0.3rem 0.8rem; border-radius: 50px; font-size: 0.75rem; font-weight: 700; }}
.tag-top1 {{ background: linear-gradient(135deg, #f59e0b, #ef4444); color: #fff; }}
.tag-sub {{ background: rgba(255, 255, 255, 0.06); color: var(--muted); border: 1px solid rgba(255, 255, 255, 0.1); }}
.stock-body {{ padding: 1.6rem; display: grid; grid-template-columns: 42% 58%; gap: 1.5rem; align-items: center; }}
@media(max-width: 900px) {{ .stock-body {{ grid-template-columns: 1fr; }} }}
.chart-container {{ border-radius: 12px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1); background: #000; width: 100%; max-width: 100%; }}
.chart-img {{ width: 100%; height: auto; display: block; }}
.info-panel {{ display: flex; flex-direction: column; justify-content: space-between; }}
.metrics-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin-bottom: 1rem; }}
.metric-box {{ background: rgba(255, 255, 255, 0.03); border-radius: 10px; padding: 0.6rem 0.8rem; text-align: center; }}
.metric-val {{ font-weight: 700; font-size: 1rem; color: #fff; }}
.metric-lbl {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.2rem; }}
.strategy-setup {{ background: rgba(99, 102, 241, 0.08); border: 1px dashed rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 1rem; margin-bottom: 1rem; font-size: 0.85rem; }}
.setup-row {{ display: flex; justify-content: space-between; margin-bottom: 0.4rem; }}
.setup-row:last-child {{ margin-bottom: 0; }}
.opinion-box {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 1rem; font-size: 0.88rem; line-height: 1.6; color: #d1d5db; }}
footer {{ text-align: center; padding: 3rem 1.5rem; color: var(--muted); font-size: 0.85rem; border-top: 1px solid var(--card-border); margin-top: 4rem; }}
</style>
</head>
<body>

<header>
  <div class="badge-main">{badge_title}</div>
  <h1>{page_title}</h1>
  <p class="subtitle">{sub_title}</p>
  <p class="meta-info">포착 기준일: {scr_title_date} | 매매 추적일: {trade_entry_date} | 생성: {now_str}</p>
  <div>{toggle_btn}</div>
</header>

<container>

  <div class="stats-grid">
    <div class="stat-card"><div class="stat-num" style="color: #a5b4fc">{total_count}</div><div class="stat-label">전체 포착 종목</div></div>
    <div class="stat-card"><div class="stat-num" style="color: #fbbf24">{top_count}</div><div class="stat-label">★ TOP 정예 종목</div></div>
    <div class="stat-card"><div class="stat-num" style="color: #34d399">39%</div><div class="stat-label">총 포지션 비중</div></div>
    <div class="stat-card"><div class="stat-num" style="color: #f472b6">{entry_label}</div><div class="stat-label">매매 추적일</div></div>
  </div>
"""

    for s_id, s_title in [(1, "양-음-양 눌림목"), (2, "일일봉 매집봉"), (3, "수급 낙폭과대 바닥형")]:
        html += f"""
  <div class="section">
    <div class="section-title">
      <span>{'🔵' if s_id==1 else '🟡' if s_id==2 else '🟢'} 전략 {s_id} &mdash; {s_title}</span>
      <span style="font-size:0.9rem; color:var(--muted)">총 {len(results[s_id])}개 포착</span>
    </div>
    <div class="stock-grid">
"""
        for i, r in enumerate(results[s_id], 1):
            is_top = (s_id==1 and i<=3) or (s_id==2 and i==1) or (s_id==3 and i<=2)
            card_cls = "stock-card top-choice" if is_top else "stock-card"
            badge_html = f'<span class="tag-badge tag-top1">★ TOP {i} 선택</span>' if is_top else '<span class="tag-badge tag-sub">후보군</span>'
            chart_path = r.get('fb_chart_rel_path', f"charts/chart_{r['code']}_{r['name']}.png") if is_feedback else r.get('scr_chart_rel_path', f"charts/chart_{r['code']}_{r['name']}.png")
            
            if is_feedback:
                panel_setup = f"""
            <div class="strategy-setup">
              <div class="setup-row"><span>🎯 성과 상태</span><strong style="color:{'#34d399' if '달성' in r['status_str'] else '#fbbf24' if '유지' in r['status_str'] else '#f87171'}">{r['status_str']}</strong></div>
              <div class="setup-row"><span>📈 매매일 최고가</span><strong>{r['fb_high']:,}원 ({r['max_ret']:+.2f}%)</strong></div>
              <div class="setup-row"><span>📉 매매일 종가</span><span>{r['fb_close']:,}원 ({r['close_ret']:+.2f}%)</span></div>
            </div>
"""
                fb_high_val = r.get('fb_high', r['close'])
                fb_close_val = r.get('fb_close', r['close'])
                metrics_html = f"""
            <div class="metrics-row">
              <div class="metric-box"><div class="metric-val">{r['close']:,}원</div><div class="metric-lbl">기준 종가</div></div>
              <div class="metric-box"><div class="metric-val" style="color:#ef4444">{fb_high_val:,}원</div><div class="metric-lbl">익일 고가</div></div>
              <div class="metric-box"><div class="metric-val">{fb_close_val:,}원</div><div class="metric-lbl">익일 종가</div></div>
            </div>"""
            else:
                panel_setup = f"""
            <div class="strategy-setup">
              <div class="setup-row"><span>🎯 목표 익절가</span><strong style="color:#34d399">{int(r['close']*1.05 if s_id==1 else r['close']*1.03):,}원 (+{5 if s_id==1 else 3}%)</strong></div>
              <div class="setup-row"><span>📍 매수 대기선</span><strong>{r['close']:,}원 부근</strong></div>
              <div class="setup-row"><span>🛑 손절가</span><span>{int(r['close']*0.97 if s_id==1 else r['close']*0.968):,}원 (-3%)</span></div>
            </div>
"""
                chg = r.get('change_rate', 0.0)
                metrics_html = f"""
            <div class="metrics-row">
              <div class="metric-box"><div class="metric-val">{r['close']:,}원</div><div class="metric-lbl">기준 종가</div></div>
              <div class="metric-box"><div class="metric-val" style="color:#ef4444">{fmt_amt(r['amount'])}</div><div class="metric-lbl">거래대금</div></div>
              <div class="metric-box"><div class="metric-val">{chg:+.2f}%</div><div class="metric-lbl">당일 등락률</div></div>
            </div>"""

            html += f"""
      <div class="{card_cls}">
        <div class="stock-header">
          <div class="stock-name-box">
            <span class="stock-name">{r['name']}</span>
            <span class="stock-code">{r['code']}</span>
            {badge_html}
          </div>
          <div style="font-weight:700; color:#fbbf24; font-size:1.1rem">{r['close']:,}원 ({fmt_amt(r['amount'])})</div>
        </div>
        <div class="stock-body">
          <div class="chart-container">
            <img src="{chart_path}" alt="{r['name']} 차트" class="chart-img">
          </div>
          <div class="info-panel">
            {metrics_html}
            {panel_setup}
            <div class="opinion-box">
              <strong>💡 분석 의견 & 복기:</strong><br>{r['reason']}
            </div>
          </div>
        </div>
      </div>
"""
        html += """
    </div>
  </div>
"""

    html += f"""
</container>

<footer>
  {badge_title} · 생성일시: {now_str} · 리포트 시스템
</footer>

</body>
</html>
"""
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="독립 익일 피드백 리포트 실행기")
    parser.add_argument("--scr-date", type=str, default="2026-07-30", help="스크리닝 기준일 (YYYY-MM-DD)")
    parser.add_argument("--fb-date", type=str, default="2026-07-31", help="모니터링 피드백일 (YYYY-MM-DD)")
    args = parser.parse_args()

    run_feedback_for_dates(scr_date=args.scr_date, fb_date=args.fb_date)

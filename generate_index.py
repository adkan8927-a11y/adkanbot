import os
import re
import json
import re
import subprocess
import sys
import pandas as pd
from datetime import datetime

def convert_md_to_html(md_path, html_path, title_str):
    # markdown 라이브러리 동적 설치 및 가져오기
    try:
        import markdown
    except ImportError:
        print("⚡ markdown 라이브러리가 존재하지 않아 자동 설치를 진행합니다...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
            import markdown
            print("✅ markdown 라이브러리 설치 성공!")
        except Exception as install_err:
            print(f"❌ markdown 라이브러리 설치 실패: {install_err}")
            return
            
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # markdown -> html 변환 (표와 코드 펜스 기능 추가)
    html_body = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
    html_body = re.sub(r'href="([^"]+)\.md"', r'href="\1.html"', html_body)

    # 루트 index.html로의 상대 경로 동적 계산 (서브폴더 404 방지)
    rel_dir = os.path.relpath(".", os.path.dirname(html_path)).replace("\\", "/")
    back_href = f"{rel_dir}/index.html" if rel_dir != "." else "index.html"

    # 템플릿 결합
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --card-border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #475569;
            --primary: #4f46e5;
            --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            --font-outfit: 'Outfit', 'Inter', sans-serif;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            line-height: 1.75;
            padding: 3rem 1.5rem;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.06) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(124, 58, 237, 0.06) 0%, transparent 40%);
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 3rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
            position: relative;
        }}

        .back-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 2rem;
            padding: 0.5rem 1rem;
            background: #e0e7ff;
            border-radius: 10px;
            transition: all 0.2s ease;
        }}

        .back-btn:hover {{
            background: #c7d2fe;
            transform: translateX(-3px);
        }}

        .back-btn svg {{
            width: 18px;
            height: 18px;
            transition: transform 0.2s ease;
        }}

        .back-btn:hover svg {{
            transform: translateX(-2px);
        }}

        h1 {{
            font-family: var(--font-outfit);
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text-main);
            margin-bottom: 1.5rem;
            line-height: 1.3;
            letter-spacing: -0.02em;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 1rem;
        }}

        h2 {{
            font-family: var(--font-outfit);
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-main);
            margin-top: 2.5rem;
            margin-bottom: 1rem;
            letter-spacing: -0.01em;
        }}

        h3 {{
            font-family: var(--font-outfit);
            font-size: 1.3rem;
            font-weight: 700;
            color: #1e1b4b;
            margin-top: 2rem;
            margin-bottom: 1rem;
            padding-left: 0.8rem;
            border-left: 4px solid var(--primary);
        }}

        blockquote {{
            background: #f1f5f9;
            border-left: 4px solid #6366f1;
            padding: 1rem 1.25rem;
            margin: 1.5rem 0;
            border-radius: 0 12px 12px 0;
            color: var(--text-muted);
            font-size: 0.95rem;
        }}

        blockquote p {{
            margin-bottom: 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            font-size: 0.92rem;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
            border: 1px solid #cbd5e1;
        }}

        th {{
            background: #f1f5f9;
            color: #0f172a;
            font-weight: 700;
            padding: 0.85rem 1rem;
            border-bottom: 2px solid #cbd5e1;
            text-align: left;
        }}

        td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e2e8f0;
            color: #334155;
        }}

        tr:nth-child(even) td {{
            background: #f8fafc;
        }}

        tr:hover td {{
            background: #eef2ff;
        }}

        img {{
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
            margin: 1.2rem 0;
        }}

        ul {{
            margin-bottom: 1.5rem;
            list-style: none;
            padding-left: 0;
        }}

        li {{
            margin-bottom: 1.5rem;
            position: relative;
            color: var(--text-muted);
            font-size: 1rem;
            line-height: 1.6;
        }}

        li a {{
            color: #4f46e5;
            font-size: 1.1rem;
            font-weight: 600;
            text-decoration: none;
            transition: color 0.2s ease;
            display: inline-block;
            margin-bottom: 0.3rem;
        }}

        li a:hover {{
            color: #4338ca;
            text-decoration: underline;
        }}

        li p {{
            color: var(--text-muted);
            font-size: 1rem;
            line-height: 1.6;
            margin-left: 0.5rem;
            display: inline;
        }}

        hr {{
            border: 0;
            height: 1px;
            background: #e2e8f0;
            margin: 2.5rem 0;
        }}

        p {{
            margin-bottom: 1rem;
            color: #334155;
        }}

        footer {{
            margin-top: 4rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid #e2e8f0;
            padding-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="{back_href}" class="back-btn">
            <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none"><path d="M19 12H5M12 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round"/></svg>
            대시보드로 돌아가기
        </a>
        
        {html_body}
        
        <footer>
            <p>© 2026 Daily Stock News Crawler System. Powered by Gemini Pro & Antigravity AI.</p>
        </footer>
    </div>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"✅ HTML 컴파일 완료: {html_path}")

def generate_index():
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    # reports 디렉토리 및 모든 월별 서브디렉토리 내의 md 파일 탐색
    report_list = []
    
    for root, _, files in os.walk(reports_dir):
        for filename in files:
            match = re.match(r"^(\d{4}-\d{2}-\d{2})_(장전|장중|장후|주말|스크리닝|피드백|5대섹터_통합분석|위클리브리핑|당일상한가급등)\.md$", filename)
            if match:
                date_str = match.group(1)
                report_type = match.group(2)
                filepath = os.path.join(root, filename)
                html_filename = filename.replace(".md", ".html")
                html_filepath = os.path.join(root, html_filename)
                
                # HTML 파일 생성 (스토커/스크리닝/피드백/당일상한가급등 등 커스텀 리치 HTML이 존재하는 경우 오버라이드 방지)
                title_str = f"{date_str} 당일 상한가/급등주 분석" if report_type == "당일상한가급등" else (f"{date_str} 위클리 브리핑" if "위클리" in report_type or "5대섹터" in report_type else (f"{date_str} {report_type} 리포트" if report_type in ("스크리닝", "피드백") else f"{date_str} {report_type} 시황 리포트"))
                is_custom_html = report_type in ("스크리닝", "피드백", "당일상한가급등") and os.path.exists(html_filepath)
                if not is_custom_html:
                    try:
                        convert_md_to_html(filepath, html_filepath, title_str)
                    except Exception as e:
                        print(f"Error compiling HTML for {filename}: {e}")
                else:
                    print(f"🎨 커스텀 리치 HTML 리포트 보존: {html_filepath}")
                
                # 상대 경로 계산 (index.html 기준 경로)
                rel_html_path = os.path.relpath(html_filepath, ".").replace("\\", "/")
                report_list.append({
                    "date": date_str,
                    "type": report_type,
                    "filename": filename,
                    "html_path": rel_html_path,
                    "summary": "당일 상한가/하한가 및 150억+15%+ 폭등주 분석 카드 리포트" if report_type == "당일상한가급등" else ("5대 주도 섹터 업황 분석 및 주간 브리핑 리포트" if report_type in ("위클리브리핑", "5대섹터_통합분석") else ("실전플랜 1 성과 추적 피드백 리포트" if report_type == "피드백" else ("실전플랜 1 기반 매매 후보 스크리닝 리포트" if report_type == "스크리닝" else "")))
                })
            
    # 날짜 및 발행 우선순위 내림차순 정렬 (동일 날짜 내: 당일상한가급등 > 피드백 > 스크리닝 > 장후 > 장중 > 장전 > 주말)
    type_order = {"당일상한가급등": 10, "피드백": 9, "스크리닝": 8, "장후": 7, "장중": 6, "장전": 5, "주말": 4, "위클리브리핑": 3, "5대섹터_통합분석": 2}
    report_list.sort(key=lambda x: (x["date"], type_order.get(x["type"], 1)), reverse=True)

    # 최근 발행된 뉴스 리포트 경로 탐색
    news_reports = [r for r in report_list if r['type'] in ('장전', '주말', '장후')]
    latest_news_path = news_reports[0]['html_path'] if news_reports else '#'

    # 최근 발행된 위클리 브리핑 경로 탐색
    weekly_reports = [r for r in report_list if r['type'] in ('위클리브리핑', '5대섹터_통합분석') or '위클리' in r['filename']]
    latest_weekly_path = weekly_reports[0]['html_path'] if weekly_reports else (report_list[0]['html_path'] if report_list else '#')

    # schedule check/master_schedule_db.csv 읽기 및 분할
    ticker_items = [] # 티커 배너용 데이터 배열
    
    csv_path = "schedule check/master_schedule_db.csv"
    vip_csv_path = "schedule check/vip_momentum_alerts.csv"
    # UTC+9 (KST) 강제 설정하여 깃허브 액션 서버에서도 한국 시간 기준으로 계산
    from datetime import timezone, timedelta
    kst = timezone(timedelta(hours=9))
    today_dt = datetime.now(kst)
    today_str = today_dt.strftime('%Y-%m-%d')
    
    if os.path.exists(csv_path):
        try:
            df_sched = pd.read_csv(csv_path)
            df_sched['date'] = df_sched['date'].astype(str).str.strip()
            df_sched = df_sched.sort_values(by='date')
            
            ipo_count = 0
            dart_count = 0
            global_count = 0
            
            major_macro = None
            major_conf = None
            major_earnings = None
            weekly_events = {i: [] for i in range(6)} # D+0 to D+5
            
            for _, row in df_sched.iterrows():
                event_date = str(row['date']).strip()
                
                # 날짜 차이 계산 (이벤트 날짜 - 오늘 날짜)
                try:
                    target_dt = datetime.strptime(event_date, '%Y-%m-%d')
                    diff_days = (target_dt.date() - today_dt.date()).days
                except:
                    continue
                
                # 과거 일정 제외
                if diff_days < 0:
                    continue
                
                category = str(row.get('category', '')).strip()
                source = str(row.get('source', '')).strip().upper()
                is_ipo = category in ('공모청약', '신규상장', '파생만기')
                is_domestic = 'DART' in source or category == '정부정책' or '오버행' in category
                
                # 국내외 공통으로 60일 이내로 제한
                if diff_days <= 60:
                    if is_ipo:
                        if ipo_count == 0:
                            ticker_items.append({"badge": "공모/상장", "date": event_date, "text": row['event']})
                            ipo_count += 1
                    elif is_domestic:
                        if 'DART' in source:
                            if dart_count == 0:
                                ticker_items.append({"badge": "기업공시/CB", "date": event_date, "text": row['event']})
                                dart_count += 1
                        else:
                            if global_count == 0:
                                ticker_items.append({"badge": "매크로/정책", "date": event_date, "text": row['event']})
                                global_count += 1
                    else:
                        if global_count == 0:
                            ticker_items.append({"badge": "글로벌학회", "date": event_date, "text": row['event']})
                        global_count += 1
                
                # [NEW] Section A & B 파싱 로직
                event_text = str(row['event']).strip()
                
                # 대시보드 표시용 이벤트 텍스트 정제 (권리락, 보호예수 중복 제거)
                if event_text.startswith("[권리락]"):
                    # [권리락] [계양전기] 유상증자 권리락 -> [계양전기] 유상증자 권리락
                    # [권리락] 계양전기 권리락 -> [계양전기] 권리락
                    cleaned = re.sub(r'^\[권리락\]\s*', '', event_text)
                    if not cleaned.startswith("["):
                        parts = cleaned.split(" ", 1)
                        if len(parts) == 2:
                            cleaned = f"[{parts[0]}] {parts[1]}"
                        else:
                            cleaned = f"[{parts[0]}]"
                    event_text = cleaned
                elif event_text.startswith("[보호예수]"):
                    # [보호예수] 카카오 의무보유 해제 (100만주) -> [카카오] 의무보유 해제 (100만주)
                    match = re.search(r'^\[보호예수\]\s*(.*?)\s*(의무보유\s*해제.*|보호예수\s*해제.*)', event_text)
                    if match:
                        event_text = f"[{match.group(1)}] {match.group(2)}"
                    else:
                        # 패턴 매칭이 안될 경우 첫 띄어쓰기를 기준으로 묶음
                        parts = event_text.replace("[보호예수]", "").strip().split(" ", 1)
                        if len(parts) == 2:
                            event_text = f"[{parts[0]}] {parts[1]}"
                # Section A
                if diff_days <= 60:
                    is_macro = (
                        source in ('FRED', 'FRED API') or 
                        category in ('정부정책', '거시 지표', '거시 일정', '국제 - 미국', '매크로') or 
                        any(kw in event_text.upper() for kw in ('FOMC', 'CPI', 'PPI', '금리', 'FED', '연준', '물가'))
                    )
                    if is_macro and not major_macro:
                        major_macro = {"date": event_date, "text": event_text, "cat": "매크로"}
                    elif (category == '글로벌학회' or category == '학회') and not major_conf:
                        major_conf = {"date": event_date, "text": event_text, "cat": "학회"}
                    elif category == '실적발표' and not major_earnings:
                        major_earnings = {"date": event_date, "text": event_text, "cat": "실적"}
                        
                # Section B (0~5일 이내) - CB/BW 오버행 및 과거 1년 공시 포함
                if 0 <= diff_days <= 5:
                    if '공시접수' in event_text:
                        continue
                    is_corp = (
                        category in ('공모청약', '신규상장', '의무보유등록해제', '파생만기', '실적발표', '오버행(잠재매도)', '오버행', 'CB/BW', '전환사채') or 
                        'DART' in source or 
                        '보호예수' in category or 
                        '오버행' in category or 
                        'CB' in event_text.upper() or 
                        '전환' in event_text or 
                        '사채' in event_text
                    )
                    if is_corp:
                        weekly_events[diff_days].append({"cat": category, "text": event_text})
        except Exception as e:
            print(f"Error loading schedule db: {e}")

    # VIP 돌발 일정 데이터 로드
    if os.path.exists(vip_csv_path):
        try:
            df_vip = pd.read_csv(vip_csv_path)
            df_vip['date_captured'] = df_vip['date_captured'].astype(str).str.strip()
            df_vip = df_vip.sort_values(by='date_captured')
            
            for _, row in df_vip.iterrows():
                event_date = str(row['date_captured']).strip()
                try:
                    target_dt = datetime.strptime(event_date, '%Y-%m-%d')
                    diff_days = (target_dt.date() - today_dt.date()).days
                except:
                    continue
                
                # 캡처일 기준 과거 3일까지는 탐색
                if diff_days >= -3:
                    timeline_str = str(row.get('estimated_timeline', 'N/A')).strip()
                    
                    # '단기', '중기' 등 모호한 표현 제외, 실제 월/일이 지정된 경우만 노출
                    if re.search(r'\d+월|\d+일', timeline_str):
                        event_text = f"[{row.get('sector', '기타')}] {row.get('issue', 'N/A')} ({timeline_str})"
                        vip_link = str(row.get('link', '')).strip()
                        ticker_items.append({"badge": "VIP모멘텀", "date": event_date, "text": event_text, "link": vip_link})
                        if len(ticker_items) >= 5:
                            break
        except Exception as e:
            print(f"Error loading vip db: {e}")

    # 실전플랜1 스크리닝 섹션 동적 HTML 조립 (최신 마크다운 기반)
    import glob
    
    scr_date_str = "최신"
    trade_date_str = "차일"
    s1_items_html = ""
    s2_items_html = ""
    s3_items_html = ""
    
    scr_files = glob.glob(os.path.join(reports_dir, "202*-*-*_스크리닝.md"))
    if scr_files:
        latest_file = sorted(scr_files)[-1]
        scr_date_str = os.path.basename(latest_file).split("_")[0]
        
        try:
            scr_dt = datetime.strptime(scr_date_str, "%Y-%m-%d")
            if scr_dt.weekday() == 4: # Friday
                next_dt = scr_dt + timedelta(days=3)
            elif scr_dt.weekday() == 5: # Saturday
                next_dt = scr_dt + timedelta(days=2)
            else:
                next_dt = scr_dt + timedelta(days=1)
            trade_date_str = next_dt.strftime("%y-%m-%d")
        except:
            trade_date_str = "차일"
            
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            res = {"1": [], "2": [], "3": []}
            current_strategy = None
            for line in content.split("\n"):
                if "전략 1 요약표" in line:
                    current_strategy = "1"
                elif "전략 2 요약표" in line:
                    current_strategy = "2"
                elif "전략 3 요약표" in line or "전략 3 —" in line:
                    current_strategy = "3"
                    
                if current_strategy and line.startswith("| **"):
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
                        is_adk = "ADK" in reason or "ADK특" in status
                        is_sawitgam = "사윗감" in status or "사윗감" in reason
                        
                        item = {
                            "name": name,
                            "close": close,
                            "support_ma": ma,
                            "sawitgam": is_sawitgam,
                            "is_adk_top1": is_adk,
                            "frgn_20": 0.0,
                            "orgn_20": 0.0,
                            "is_top": is_top,
                            "is_candidate": is_candidate
                        }
                        
                        if current_strategy == "3":
                            m_orgn = re.search(r"기관\s*([+-]?\d+)억", reason)
                            m_frgn = re.search(r"외인\s*([+-]?\d+)억", reason)
                            if m_orgn: item["orgn_20"] = int(m_orgn.group(1)) * 1e8
                            if m_frgn: item["frgn_20"] = int(m_frgn.group(1)) * 1e8
                        
                        res[current_strategy].append(item)
                        
            # 전략 1 (TOP 3)
            s1_list = [x for x in res["1"] if x["is_top"]] or res["1"]
            for i, item in enumerate(s1_list[:3]):
                name = item["name"]
                close = item["close"]
                ma = item.get("support_ma", "5일선")
                cond_parts = []
                if item.get("sawitgam"): cond_parts.append("사윗감")
                if item.get("is_adk_top1"): cond_parts.append("ADK특")
                cond_str = f' ({", ".join(cond_parts)})' if cond_parts else ""
                s1_items_html += f'<li style="line-height: 1.4; margin-bottom: 0;">★ <b>[{name}]</b> {close:,}원 | {ma} 지지{cond_str}</li>'
            if not s1_items_html:
                s1_items_html = '<li style="line-height: 1.4; color:#64748b;">포착 종목 없음</li>'

            # 전략 2 (TOP 1 + 후보)
            s2_list = res["2"]
            for i, item in enumerate(s2_list[:3]):
                icon = "★ " if i == 0 else "• "
                color_style = "" if i == 0 else " color:#64748b;"
                name = item["name"]
                close = item["close"]
                ma = item.get("support_ma", "240일선")
                tag = " (이일홍)" if i == 0 else " (후보)"
                s2_items_html += f'<li style="line-height: 1.4; margin-bottom: 0;{color_style}">{icon}<b>[{name}]</b> {close:,}원 | {ma} 지지{tag}</li>'
            if not s2_items_html:
                s2_items_html = '<li style="line-height: 1.4; color:#64748b;">포착 종목 없음</li>'

            # 전략 3 (TOP 2 + 후보)
            s3_list = res["3"]
            for i, item in enumerate(s3_list[:3]):
                icon = "★ " if i < 2 else "• "
                color_style = "" if i < 2 else " color:#64748b;"
                name = item["name"]
                close = item["close"]
                orgn_amt = item.get("orgn_20", 0) / 1e8
                frgn_amt = item.get("frgn_20", 0) / 1e8
                sugeub_parts = []
                if orgn_amt != 0: sugeub_parts.append(f"기관 {orgn_amt:+.0f}억")
                if frgn_amt != 0: sugeub_parts.append(f"외인 {frgn_amt:+.0f}억")
                sugeub_str = " / ".join(sugeub_parts) if sugeub_parts else "메이저 수급 유입"
                tag = "" if i < 2 else " (후보)"
                s3_items_html += f'<li style="line-height: 1.4; margin-bottom: 0;{color_style}">{icon}<b>[{name}]</b> {close:,}원 | {sugeub_str}{tag}</li>'
            if not s3_items_html:
                s3_items_html = '<li style="line-height: 1.4; color:#64748b;">포착 종목 없음</li>'

        except Exception as snap_err:
            print(f"Error parsing latest screening md: {snap_err}")

    # 기본 폴백
    if not s1_items_html:
        s1_items_html = '<li style="line-height: 1.4; margin-bottom: 0;">★ <b>[삼성전자]</b> 239,500원 | 3일선 지지</li>'
        s2_items_html = '<li style="line-height: 1.4; margin-bottom: 0;">★ <b>[파세코]</b> 7,300원 | 240일선 지지 (이일홍)</li>'
        s3_items_html = '<li style="line-height: 1.4; margin-bottom: 0;">★ <b>[코오롱티슈진]</b> 14,290원 | 메이저 수급</li>'

    import sys
    sys.path.append("/Users/adkan/adkan연구2/schedule check/agents")
    try:
        from broker_report_agent import BrokerReportAgent
        target_date = datetime.now().strftime("%Y-%m-%d")
        md_table = BrokerReportAgent.format_standard_dashboard(target_date)
        if md_table:
            import markdown
            html_table = markdown.markdown(md_table, extensions=['tables'])
            section_upgrades_html = f"""
            <div style="background: #ffffff; border: 1px solid #e9d5ff; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(168, 85, 247, 0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.0rem; flex-wrap: wrap; gap: 0.5rem;">
                    <h3 style="font-size: 1.05rem; font-weight: 700; color: #7e22ce; display: flex; align-items: center; gap: 0.5rem; margin: 0; border: none; padding: 0;">
                        🔥 [기관 리포트] 당일 목표가 상향 종목 <span style="font-size: 0.75rem; background: #f3e8ff; color: #6b21a8; padding: 0.2rem 0.6rem; border-radius: 50px; font-weight: 600;">FnGuide/Naver 수집</span>
                    </h3>
                </div>
                <div style="background: #ffffff; border: 1px solid #f3e8ff; border-radius: 8px; padding: 0.8rem; overflow-x: auto;">
                    {html_table}
                </div>
            </div>
            """
        else:
            section_upgrades_html = ""
    except Exception as e:
        print(f"⚠️ broker_report_agent 로딩 실패: {e}")
        section_upgrades_html = ""

    section_screener_html = f"""
    <div style="background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); border: 1px solid #a7f3d0; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.06);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; flex-wrap: wrap; gap: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #047857; display: flex; align-items: center; gap: 0.5rem; margin: 0; border: none; padding: 0;">
                📈 [실전플랜 1] {trade_date_str} 추천 매매 종목 <span style="font-size: 0.8rem; background: #d1fae5; color: #065f46; padding: 0.25rem 0.75rem; border-radius: 50px; font-weight: 600;">{scr_date_str} 종가 스캔</span>
            </h3>
            <a href="reports/{scr_date_str}_스크리닝.html" style="text-decoration: none; color: #047857; font-size: 0.85rem; font-weight: 700; display: inline-flex; align-items: center; gap: 0.3rem; background: #ffffff; border: 1px solid #a7f3d0; padding: 0.4rem 0.9rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.1); transition: all 0.2s;">
                전체 스크리닝 리포트 보기 &rarr;
            </a>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 800px; margin: 0 auto;">
            <!-- 전략 1 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">🔵 전략 1 눌림목</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">TOP 선택</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    {s1_items_html}
                </ul>
            </div>

            <!-- 전략 2 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #fef3c7; color: #92400e; border: 1px solid #fde68a; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">🟡 전략 2 매집봉</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">TOP 선택</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    {s2_items_html}
                </ul>
            </div>

            <!-- 전략 3 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">🟢 전략 3 수급바닥</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">TOP 선택</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    {s3_items_html}
                </ul>
            </div>
        </div>
    </div>
    """

    section_beta_html = ""

    # Section A HTML 조립
    section_a_html = f"""
    <div class="major-events-panel" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);">
        <h3 style="margin-bottom: 1.2rem; font-size: 1.15rem; display: flex; align-items: center; gap: 0.5rem; color: #0f172a; border: none; padding: 0;">🌟 핵심 주도 이벤트 <span style="font-size: 0.8rem; color: #64748b; font-weight: normal;">증시 방향성을 결정하는 주요 일정</span></h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
    """
    for item in filter(None, [major_macro, major_conf, major_earnings]):
        badge_bg = "#e0f2fe" if item["cat"] == "매크로" else "#f3e8ff" if item["cat"] == "학회" else "#d1fae5"
        badge_text = "#0369a1" if item["cat"] == "매크로" else "#6b21a8" if item["cat"] == "학회" else "#065f46"
        badge_border = "#bae6fd" if item["cat"] == "매크로" else "#e9d5ff" if item["cat"] == "학회" else "#a7f3d0"
        section_a_html += f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 1.2rem; border-radius: 12px; display: flex; flex-direction: column; gap: 0.8rem; transition: transform 0.2s; cursor: default;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="background: {badge_bg}; color: {badge_text}; border: 1px solid {badge_border}; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">{item['cat']}</span>
                    <span style="color: #d97706; font-weight: 700; font-size: 0.85rem;">{item['date']}</span>
                </div>
                <div style="font-size: 0.95rem; line-height: 1.45; color: #0f172a; font-weight: 600;">{item['text']}</div>
            </div>
        """
    if not any([major_macro, major_conf, major_earnings]):
         section_a_html += "<div style='color: #64748b; font-size: 0.9rem;'>예정된 핵심 이벤트가 없습니다.</div>"
    section_a_html += "</div></div>"

    # Section B HTML 조립
    section_b_html = f"""
    <div class="weekly-preview-panel" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.5rem; margin-bottom: 2.5rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);">
        <h3 style="margin-bottom: 1.2rem; font-size: 1.15rem; display: flex; align-items: center; gap: 0.5rem; color: #0f172a; border: none; padding: 0;">📅 단기 주간 캘린더 (D~D+5)</h3>
        <div style="display: flex; flex-direction: column; gap: 0.8rem;">
    """
    day_names = {0: "오늘", 1: "내일", 2: "모레"}
    has_weekly = False
    for d in range(6):
        if weekly_events[d]:
            has_weekly = True
            target_date = today_dt + timedelta(days=d)
            date_str = target_date.strftime('%m/%d')
            day_kor = ["월", "화", "수", "목", "금", "토", "일"][target_date.weekday()]
            prefix = day_names.get(d, f"D+{d}" if d > 0 else "D-Day")
            
            events_html = ""
            for ev in weekly_events[d]:
                events_html += f"""
                    <div style="display: flex; align-items: flex-start; gap: 0.6rem; margin-bottom: 0.5rem;">
                        <span style="color: #1e293b; font-size: 0.9rem; line-height: 1.4;">• {ev['text']}</span>
                    </div>
                """
                
            section_b_html += f"""
            <div style="display: flex; gap: 1rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.8rem;">
                <div style="flex: 0 0 110px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <div style="color: #d97706; font-weight: 700; font-size: 0.95rem; margin-bottom: 0.2rem;">{prefix}</div>
                    <div style="color: #64748b; font-size: 0.8rem; font-weight: 500;">{date_str} ({day_kor})</div>
                </div>
                <div style="flex: 1; display: flex; flex-direction: column;">
                    {events_html}
                </div>
            </div>
            """
            
    if not has_weekly:
        section_b_html += "<div style='color: #64748b; font-size: 0.9rem; padding: 0.5rem 0;'>향후 5일 이내 예정된 일반 일정이 없습니다.</div>"
    section_b_html += "</div></div>"

    # 실시간 최신 종합 투자 정보 포털 (Unified Live Collection Container with Tab Switching)
    section_live_hub_html = f"""
    <div class="live-hub-panel" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.5rem; margin-bottom: 2.5rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);">
        <div style="margin-bottom: 1.2rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <h3 style="font-size: 1.2rem; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 0.5rem; margin: 0; border: none; padding: 0;">
                ⚡ 실시간 최신 종합 투자 정보 포털
            </h3>
            <div class="hub-tab-buttons" style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <button class="hub-tab-btn active" onclick="switchHubTab('screener', this)" style="padding: 0.55rem 1.1rem; border-radius: 50px; font-weight: 700; font-size: 0.85rem; border: 1px solid #10b981; background: #ecfdf5; color: #047857; cursor: pointer; transition: all 0.2s;">📈 추천매매종목</button>
                <button class="hub-tab-btn" onclick="switchHubTab('upgrades', this)" style="padding: 0.55rem 1.1rem; border-radius: 50px; font-weight: 700; font-size: 0.85rem; border: 1px solid #cbd5e1; background: #ffffff; color: #64748b; cursor: pointer; transition: all 0.2s;">🔥 기관리포트</button>
                <button class="hub-tab-btn" onclick="switchHubTab('calendar', this)" style="padding: 0.55rem 1.1rem; border-radius: 50px; font-weight: 700; font-size: 0.85rem; border: 1px solid #cbd5e1; background: #ffffff; color: #64748b; cursor: pointer; transition: all 0.2s;">📅 주간캘린더</button>
            </div>
        </div>
        
        <div class="hub-tab-contents">
            <div id="hubTabScreener" class="hub-tab-content" style="display: block;">
                {section_screener_html}
            </div>
            <div id="hubTabUpgrades" class="hub-tab-content" style="display: none;">
                {section_upgrades_html}
            </div>
            <div id="hubTabCalendar" class="hub-tab-content" style="display: none;">
                {section_b_html}
            </div>
        </div>
    </div>
    """

    # index.html 파일 작성
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Stock News Portal</title>
    <meta name="description" content="네이버 뉴스 및 해외 RSS 기반 AI 요약 데일리 뉴스 리포트 저장소">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --card-border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #475569;
            --primary: #4f46e5;
            --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            --glow: 0 4px 20px rgba(79, 70, 229, 0.18);
            --font-outfit: 'Outfit', 'Inter', sans-serif;
            --highlight-bg: #fef2f2;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.06) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.05) 0%, transparent 40%);
            background-attachment: fixed;
        }}

        header {{
            padding: 4rem 2rem 2rem;
            text-align: center;
            position: relative;
        }}

        .logo-area {{
            display: inline-block;
            margin-bottom: 1rem;
        }}

        .logo-badge {{
            background: var(--primary-gradient);
            color: white;
            padding: 0.4rem 1.1rem;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.25);
        }}

        h1 {{
            font-family: var(--font-outfit);
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #0f172a 0%, #312e81 60%, #6d28d9 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
        }}

        header p {{
            color: var(--text-muted);
            font-size: 1.15rem;
            max-width: 620px;
            margin: 0 auto 1.8rem;
            line-height: 1.6;
        }}

        /* 티커 배너 컨테이너 */
        .ticker-container {{
            max-width: 850px;
            margin: 0 auto 2.5rem;
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            padding: 1rem 1.5rem;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
            position: relative;
            overflow: hidden;
            height: 60px;
        }}

        .ticker-icon {{
            font-size: 1.2rem;
            margin-right: 1rem;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.1); opacity: 0.7; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}

        .ticker-viewport {{
            flex: 1;
            position: relative;
            height: 100%;
            display: flex;
            align-items: center;
            overflow: hidden;
        }}

        .ticker-item {{
            position: absolute;
            left: 0;
            width: 100%;
            display: flex;
            align-items: center;
            gap: 1rem;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}

        .ticker-item.active {{
            opacity: 1;
            transform: translateY(0);
        }}

        .ticker-item.exit {{
            opacity: 0;
            transform: translateY(20px);
        }}

        .ticker-badge {{
            background: #4f46e5;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            color: white;
            white-space: nowrap;
        }}

        .ticker-date {{
            color: #d97706;
            font-weight: 700;
            font-size: 0.85rem;
            white-space: nowrap;
        }}

        .ticker-text {{
            color: #1e293b;
            font-size: 0.95rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 600;
        }}

        .search-filter-container {{
            width: 100%;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 1.2rem;
            border-radius: 20px;
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
            margin-bottom: 1.5rem;
        }}

        .search-box {{
            position: relative;
            max-width: 400px;
            flex: 1;
        }}

        .search-box input {{
            width: 100%;
            padding: 0.9rem 1.4rem;
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            color: #0f172a;
            font-size: 0.95rem;
            font-weight: 500;
            transition: all 0.25s ease;
        }}

        .search-box input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
            background: #ffffff;
        }}

        .filter-buttons {{
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .filter-btn {{
            padding: 0.6rem 1.3rem;
            border-radius: 10px;
            border: 1px solid #cbd5e1;
            background: #f8fafc;
            color: #475569;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .filter-btn:hover {{
            background: #e2e8f0;
            color: #0f172a;
        }}

        .filter-btn.active {{
            background: var(--primary);
            border-color: var(--primary);
            color: white;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
        }}

        main {{
            flex: 1;
            max-width: 880px;
            width: 100%;
            margin: 2rem auto 4rem;
            padding: 0 1.5rem;
        }}

        /* 1단 와이드 대시보드 레이아웃 */
        .dashboard-layout {{
            display: block;
            width: 100%;
        }}

        /* 우측 뉴스 카드 그리드 래퍼 */
        .grid-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 0;
            min-height: 0;
        }}

        .grid-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
            gap: 1.8rem;
            transition: all 0.3s ease;
            overflow-y: auto;
            max-height: 800px; /* 카드 3행에 해당하는 높이 */
            padding-right: 4px;
            scroll-behavior: smooth;
        }}

        /* 스크롤바 스타일 */
        .grid-container::-webkit-scrollbar {{
            width: 6px;
        }}
        .grid-container::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .grid-container::-webkit-scrollbar-thumb {{
            background: #cbd5e1;
            border-radius: 10px;
        }}

        /* 더보기/접기 버튼 */
        .grid-toggle-btn {{
            margin-top: 1.5rem;
            align-self: center;
            background: #ffffff;
            border: 1px solid #cbd5e1;
            color: #475569;
            font-size: 0.85rem;
            font-family: var(--font-inter);
            font-weight: 600;
            padding: 0.6rem 1.6rem;
            border-radius: 999px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
            transition: all 0.2s ease;
        }}
        .grid-toggle-btn:hover {{
            background: #f1f5f9;
            border-color: #4f46e5;
            color: #4f46e5;
        }}

        .card {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            padding: 1.8rem;
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
        }}

        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--primary-gradient);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .card:hover {{
            transform: translateY(-6px);
            border-color: #c7d2fe;
            box-shadow: 0 16px 36px rgba(79, 70, 229, 0.12);
        }}

        .card:hover::before {{
            opacity: 1;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .date-text {{
            font-family: var(--font-outfit);
            font-size: 1.2rem;
            font-weight: 800;
            color: #0f172a;
        }}

        .badge {{
            padding: 0.35rem 0.85rem;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 700;
        }}

        .badge.장전 {{
            background: #e0e7ff;
            color: #3730a3;
            border: 1px solid #c7d2fe;
        }}

        .badge.장중 {{
            background: #e0f2fe;
            color: #0369a1;
            border: 1px solid #bae6fd;
        }}

        .badge.장후 {{
            background: #fce7f3;
            color: #be185d;
            border: 1px solid #fbcfe8;
        }}

        .badge.주말 {{
            background: #ffedd5;
            color: #c2410c;
            border: 1px solid #fed7aa;
        }}

        .badge.스크리닝 {{
            background: #d1fae5;
            color: #047857;
            border: 1px solid #a7f3d0;
        }}

        /* 통합 아카이브 패널 스타일 */
        .archive-panel {{
            background: #ffffff;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
            overflow: hidden;
            margin-bottom: 3rem;
            margin-top: 1rem;
        }}

        .archive-header {{
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            padding: 1.2rem;
            display: flex;
            justify-content: center;
        }}

        .reports-archive-layout {{
            display: flex;
            flex-direction: row;
            align-items: stretch;
            min-height: 500px;
        }}

        .month-sidebar {{
            width: 220px;
            flex-shrink: 0;
            background: #ffffff;
            border-right: 1px solid #e2e8f0;
            padding: 1.5rem;
        }}

        .month-sidebar h3 {{
            font-size: 1.1rem;
            color: #1e293b;
            margin-bottom: 1rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid #e2e8f0;
        }}

        .month-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }}

        .month-item {{
            padding: 0.75rem 1rem;
            border-radius: 8px;
            color: #475569;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.2s;
        }}

        .month-item:hover {{
            background: #f1f5f9;
            color: #0f172a;
        }}

        .month-item.active {{
            background: var(--primary-gradient);
            color: white;
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.2);
        }}

        .category-content {{
            flex-grow: 1;
            padding: 1.5rem;
            background: #fafaf9;
        }}
        
        .category-section {{
            margin-bottom: 3.5rem;
        }}

        .category-title {{
            font-size: 1.35rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 1.2rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.6rem;
        }}

        .badge.피드백 {{
            background: #fef3c7;
            color: #b45309;
            border: 1px solid #fde68a;
        }}

        .card p {{
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.6;
            flex-grow: 1;
        }}

        .view-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.75rem 1.4rem;
            border-radius: 12px;
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            color: #1e293b;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.9rem;
            transition: all 0.2s ease;
            gap: 0.5rem;
        }}

        .view-link:hover {{
            background: #4f46e5;
            color: white;
            border-color: #4f46e5;
        }}

        .view-link svg {{
            width: 16px;
            height: 16px;
            fill: currentColor;
            transition: transform 0.2s ease;
        }}

        .view-link:hover svg {{
            transform: translateX(4px);
        }}

        footer {{
            padding: 3rem 2rem;
            text-align: center;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
            font-size: 0.85rem;
        }}

        .no-results {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 4rem;
            color: #64748b;
            font-size: 1.1rem;
        }}

        .schedule-carousel {{
            display: flex;
            flex-direction: column;
            gap: 0;
        }}

        .schedule-carousel-item {{
            width: 100%;
            margin-bottom: 2rem;
        }}

        .schedule-carousel-item:last-child {{
            margin-bottom: 0;
        }}

        .mobile-swipe-hint {{
            display: none;
            text-align: right;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 0.8rem;
        }}

        @media (max-width: 1024px) {{
            .dashboard-layout {{
                grid-template-columns: 1fr;
                gap: 2.5rem;
            }}
            .search-filter-container {{
                flex-direction: column;
                align-items: stretch;
                gap: 1rem;
            }}
            .search-box {{
                max-width: 100%;
            }}
            .schedule-carousel {{
                flex-direction: row;
                overflow-x: auto;
                scroll-snap-type: x mandatory;
                gap: 1.5rem;
                padding-bottom: 1rem;
                scrollbar-width: none;
                -ms-overflow-style: none;
            }}
            .schedule-carousel::-webkit-scrollbar {{
                display: none;
            }}
            .schedule-carousel-item {{
                flex: 0 0 90%;
                scroll-snap-align: start;
                margin-bottom: 0;
            }}
            .mobile-swipe-hint {{
                display: block;
            }}
        }}

        @media (max-width: 768px) {{
            header {{
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                gap: 1rem;
            }}
            .header-content, h1, .logo-area, p {{
                text-align: center !important;
                margin-left: auto;
                margin-right: auto;
            }}
            h1 {{
                font-size: 2.2rem;
            }}
            .grid-container {{
                grid-template-columns: 1fr;
            }}
            .dashboard-layout {{
                width: 95%;
                margin: 0 auto;
            }}
            .schedule-panel {{
                padding: 1.5rem 1rem;
            }}
            .schedule-carousel-item {{
                flex: 0 0 95%;
            }}
            .filter-buttons {{
                gap: 0.5rem;
            }}
            .filter-btn {{
                padding: 0.5rem 1rem;
                font-size: 0.85rem;
            }}
        }}
    </style>
</head>
<body>

    <header>
        <div class="logo-area">
            <span class="logo-badge">Auto Intelligence</span>
        </div>
        <h1>Daily News Hub</h1>
        <p>인공지능 에이전트가 매일 자동으로 요약하고 분석하는 국내 주요 산업군 및 핵심 글로벌 리포트 저장소입니다.</p>
        
        <div style="margin-bottom: 2.5rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            
            <a href="{latest_news_path}" style="text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; background: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; padding: 0.85rem 1.6rem; border-radius: 50px; font-weight: 700; font-size: 0.95rem; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04); transition: transform 0.2s ease, background 0.2s ease;" onmouseover="this.style.transform='translateY(-2px)'; this.style.background='#f8fafc'" onmouseout="this.style.transform='translateY(0)'; this.style.background='#ffffff'">
                📰 최근 발행된 뉴스 리포트 보기 &rarr;
            </a>
            <a href="schedule check/schedule.html" style="text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; background: var(--primary-gradient); color: white; border: none; padding: 0.85rem 1.6rem; border-radius: 50px; font-weight: 700; font-size: 0.95rem; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.25); transition: transform 0.2s ease, box-shadow 0.2s ease;" onmouseover="this.style.transform='translateY(-2px)';" onmouseout="this.style.transform='translateY(0)';">
                📅 글로벌 투자 일정 대시보드 바로가기 &rarr;
            </a>
        </div>
        
        <!-- 실시간 티커 배너 -->
        <div class="ticker-container">
            <div class="ticker-icon">⚡</div>
            <div class="ticker-viewport" id="tickerViewport">
                <!-- 자바스크립트로 동적 렌더링 -->
            </div>
        </div>
    </header>

    <main>
        <div class="dashboard-layout">
            <div class="grid-wrapper">
                
                {section_a_html}
                
                {section_live_hub_html}

                <div class="archive-panel">
                    <div class="archive-header">
                        <div class="filter-buttons" style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                            <button class="filter-btn" onclick="filterType('위클리', this)">📅 위클리브리핑</button>
                            <button class="filter-btn active" onclick="filterType('상한가', this)">🔥 당일상한가</button>
                            <button class="filter-btn" onclick="filterType('매매', this)">💼 매매리포트</button>
                            <button class="filter-btn" onclick="filterType('장전', this)">🌅 장전</button>
                            <button class="filter-btn" onclick="filterType('장후', this)">🌆 장후</button>
                            <button class="filter-btn" onclick="filterType('주말', this)">📅 주말</button>
                        </div>
                    </div>
                    <div class="reports-archive-layout">
                        <aside class="month-sidebar">
                            <h3>📅 월별 아카이브</h3>
                            <ul id="monthList" class="month-list">
                                <!-- JS 동적 렌더링 -->
                            </ul>
                        </aside>
                        <div class="category-content">
                            <div class="grid-container" id="reportsGrid">
                                <!-- 자바스크립트 동적 렌더링 -->
                            </div>
                            <button class="grid-toggle-btn" id="gridToggleBtn" onclick="toggleGridExpand()">
                                <span id="gridToggleLabel">▼ 더보기</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <p>© 2026 Daily Stock News Crawler System. Powered by Gemini Pro & Antigravity AI.</p>
    </footer>

    <script>
        const reportsData = {json.dumps(report_list, ensure_ascii=False)};
        const tickerData = {json.dumps(ticker_items, ensure_ascii=False)};
        
        // --- 티커 배너 로직 ---
        let currentTickerIndex = 0;
        
        function initTicker() {{
            const viewport = document.getElementById('tickerViewport');
            if (!tickerData || tickerData.length === 0) {{
                viewport.innerHTML = `<div class="ticker-item active"><span class="ticker-text">예정된 주요 일정이 없습니다.</span></div>`;
                return;
            }}
            
            // 초기 DOM 생성
            tickerData.forEach((item, index) => {{
                const el = item.link && item.link !== 'nan' ? document.createElement('a') : document.createElement('div');
                el.className = `ticker-item ${{index === 0 ? 'active' : ''}}`;
                el.id = `ticker-item-${{index}}`;
                if (item.link && item.link !== 'nan') {{
                    el.href = item.link;
                    el.target = "_blank";
                    el.style.textDecoration = "none";
                }}
                el.innerHTML = `
                    <span class="ticker-badge">${{item.badge}}</span>
                    <span class="ticker-date">${{item.date}}</span>
                    <span class="ticker-text">${{item.text}}</span>
                `;
                viewport.appendChild(el);
            }});
            
            if (tickerData.length > 1) {{
                setInterval(rotateTicker, 3500); // 3.5초마다 회전
            }}
        }}
        
        function rotateTicker() {{
            const prevIndex = currentTickerIndex;
            currentTickerIndex = (currentTickerIndex + 1) % tickerData.length;
            
            const prevEl = document.getElementById(`ticker-item-${{prevIndex}}`);
            const nextEl = document.getElementById(`ticker-item-${{currentTickerIndex}}`);
            
            // 이전 요소는 아래로 빠짐
            prevEl.className = 'ticker-item exit';
            
            // 다음 요소는 위에서 들어옴
            // 브라우저 렌더링 사이클을 위해 잠시 대기 후 active 클래스 부여
            nextEl.className = 'ticker-item'; 
            setTimeout(() => {{
                nextEl.className = 'ticker-item active';
            }}, 50);
        }}

        let selectedMonth = '';
        let currentFilter = '상한가';
        let gridExpanded = false;
        const COLLAPSED_HEIGHT = '2400px';

        // --- 월별 사이드바 초기화 ---
        function initMonthSidebar() {{
            const monthsSet = new Set();
            reportsData.forEach(r => {{
                if(r.type === '장중') return; // 장중 제외
                const m = r.date.substring(0, 7); // YYYY-MM
                monthsSet.add(m);
            }});
            const availableMonths = Array.from(monthsSet).sort().reverse();
            
            const monthList = document.getElementById('monthList');
            if(availableMonths.length > 0) {{
                selectedMonth = availableMonths[0]; // 최신 월 기본 선택
            }}

            availableMonths.forEach(m => {{
                const li = document.createElement('li');
                li.className = `month-item ${{m === selectedMonth ? 'active' : ''}}`;
                li.textContent = m.replace('-', '년 ') + '월';
                li.onclick = () => {{
                    document.querySelectorAll('.month-item').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    selectedMonth = m;
                    renderReports();
                }};
                monthList.appendChild(li);
            }});
        }}

        function switchHubTab(tabName, btn) {{
            const btns = document.querySelectorAll('.hub-tab-btn');
            btns.forEach(b => {{
                b.style.background = '#ffffff';
                b.style.color = '#64748b';
                b.style.borderColor = '#cbd5e1';
                b.classList.remove('active');
            }});
            
            btn.classList.add('active');
            if (tabName === 'screener') {{
                btn.style.background = '#ecfdf5';
                btn.style.color = '#047857';
                btn.style.borderColor = '#10b981';
            }} else if (tabName === 'upgrades') {{
                btn.style.background = '#f3e8ff';
                btn.style.color = '#6b21a8';
                btn.style.borderColor = '#c084fc';
            }} else if (tabName === 'calendar') {{
                btn.style.background = '#eff6ff';
                btn.style.color = '#1d4ed8';
                btn.style.borderColor = '#3b82f6';
            }}

            document.getElementById('hubTabScreener').style.display = (tabName === 'screener') ? 'block' : 'none';
            document.getElementById('hubTabUpgrades').style.display = (tabName === 'upgrades') ? 'block' : 'none';
            document.getElementById('hubTabCalendar').style.display = (tabName === 'calendar') ? 'block' : 'none';
        }}

        function filterType(type, element) {{
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            renderReports();
        }}

        // --- 카테고리 & 월별 렌더링 ---
        function renderReports() {{
            const grid = document.getElementById('reportsGrid');
            grid.innerHTML = '';
            
            const filtered = reportsData.filter(r => {{
                if (r.type === '장중') return false;
                if (!r.date.startsWith(selectedMonth)) return false;
                
                if (currentFilter === 'all') return true;
                if (currentFilter === '상한가' && r.type === '당일상한가급등') return true;
                if (currentFilter === '매매' && (r.type === '스크리닝' || r.type === '피드백')) return true;
                if (currentFilter === '장전' && r.type === '장전') return true;
                if (currentFilter === '장후' && r.type === '장후') return true;
                if (currentFilter === '위클리' && (r.type === '위클리브리핑' || r.type === '5대섹터_통합분석')) return true;
                if (currentFilter === '주말' && r.type === '주말') return true;
                
                return false;
            }});

            if (filtered.length === 0) {{
                grid.innerHTML = `<div class="no-results">해당 조건에 맞는 리포트가 존재하지 않습니다.</div>`;
                document.getElementById('gridToggleBtn').style.display = 'none';
                return;
            }}

            filtered.forEach(r => {{
                const dateObj = new Date(r.date);
                const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
                const weekday = weekdays[dateObj.getDay()];
                
                const card = document.createElement('div');
                card.className = 'card';
                let displayType = r.type;
                let dateDisplay = `${{r.date}} (${{weekday}})`;
                if(r.type === '당일상한가급등') displayType = '상한가/급등';
                if(r.type === '위클리브리핑' || r.type === '5대섹터_통합분석') {{
                    displayType = '위클리';
                    const weekNum = Math.ceil(dateObj.getDate() / 7);
                    dateDisplay = `${{dateObj.getMonth() + 1}}월 ${{weekNum}}주차`;
                }}
                
                card.innerHTML = `
                    <div class="card-header">
                        <span class="date-text">${{dateDisplay}}</span>
                        <span class="badge ${{r.type}}">${{displayType}} 뉴스</span>
                    </div>
                    <p>${{r.summary}}</p>
                    <a href="${{r.html_path}}" class="view-link">
                        리포트 보기
                        <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </a>
                `;
                grid.appendChild(card);
            }});

            gridExpanded = false;
            grid.style.maxHeight = COLLAPSED_HEIGHT;
            const btn = document.getElementById('gridToggleBtn');
            const label = document.getElementById('gridToggleLabel');
            if (grid.scrollHeight <= grid.clientHeight + 10) {{
                btn.style.display = 'none';
            }} else {{
                btn.style.display = 'flex';
                label.textContent = '▼ 더보기';
            }}
        }}

        function toggleGridExpand() {{
            const grid = document.getElementById('reportsGrid');
            const label = document.getElementById('gridToggleLabel');
            gridExpanded = !gridExpanded;
            if (gridExpanded) {{
                grid.style.maxHeight = grid.scrollHeight + 'px';
                label.textContent = '▲ 접기';
            }} else {{
                grid.style.maxHeight = COLLAPSED_HEIGHT;
                grid.scrollTop = 0;
                label.textContent = '▼ 더보기';
            }}
        }}

        // 초기 렌더링
        window.onload = () => {{
            initTicker();
            initMonthSidebar();
            renderReports();
        }};

    </script>
</body>
</html>
"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ index.html이 성공적으로 빌드되었습니다!")

if __name__ == "__main__":
    generate_index()

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
                radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.05) 0%, transparent 40%);
            background-attachment: fixed;
        }}

        .container {{
            max-width: 920px;
            margin: 0 auto;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 3rem;
            border-radius: 24px;
            box-shadow: 0 10px 40px rgba(15, 23, 42, 0.05);
        }}

        .back-btn {{
            display: inline-flex;
            align-items: center;
            color: var(--text-muted);
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            padding: 0.5rem 1.1rem;
            border-radius: 10px;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 2.5rem;
            transition: all 0.2s ease;
            gap: 0.5rem;
        }}

        .back-btn:hover {{
            color: #0f172a;
            background: #e2e8f0;
            border-color: #94a3b8;
        }}

        .back-btn svg {{
            width: 18px;
            height: 18px;
            fill: currentColor;
            transition: transform 0.2s ease;
        }}

        .back-btn:hover svg {{
            transform: translateX(-4px);
        }}

        h1 {{
            font-family: var(--font-outfit);
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #0f172a 0%, #312e81 60%, #6d28d9 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
            line-height: 1.25;
        }}

        h2, h3, h4 {{
            font-family: var(--font-outfit);
            color: #0f172a;
            margin-top: 2.5rem;
            margin-bottom: 1.2rem;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }}

        blockquote {{
            border-left: 4px solid var(--primary);
            padding: 0.85rem 1.25rem;
            background: #eef2ff;
            border-radius: 4px 12px 12px 4px;
            color: #1e1b4b;
            font-weight: 500;
            margin: 1.5rem 0 2rem;
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
        <a href="../index.html" class="back-btn">
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
                
                # HTML 파일 생성
                title_str = f"{date_str} 당일 상한가/급등주 분석" if report_type == "당일상한가급등" else (f"{date_str} 위클리 브리핑" if "위클리" in report_type or "5대섹터" in report_type else (f"{date_str} {report_type} 리포트" if report_type in ("스크리닝", "피드백") else f"{date_str} {report_type} 시황 리포트"))
                try:
                    convert_md_to_html(filepath, html_filepath, title_str)
                except Exception as e:
                    print(f"Error compiling HTML for {filename}: {e}")
                
                # 상대 경로 계산 (index.html 기준 경로)
                rel_html_path = os.path.relpath(html_filepath, ".").replace("\\", "/")
                report_list.append({
                    "date": date_str,
                    "type": report_type,
                    "filename": filename,
                    "html_path": rel_html_path,
                    "summary": "당일 상한가/하한가 및 150억+15%+ 폭등주 분석 카드 리포트" if report_type == "당일상한가급등" else ("5대 주도 섹터 업황 분석 및 주간 브리핑 리포트" if report_type in ("위클리브리핑", "5대섹터_통합분석") else ("실전플랜 1 성과 추적 피드백 리포트" if report_type == "피드백" else ("실전플랜 1 기반 매매 후보 스크리닝 리포트" if report_type == "스크리닝" else "")))
                })
            
    # 날짜 내림차순 정렬
    type_order = {"당일상한가급등": 0.3, "피드백": 0.4, "스크리닝": 0.5, "위클리브리핑": 0.6, "5대섹터_통합분석": 0.7, "장전": 1, "장중": 1.5, "장후": 2, "주말": 3}
    report_list.sort(key=lambda x: (x["date"], type_order.get(x["type"], 9)), reverse=True)

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
                is_domestic = source == 'DART' or category == '정부정책'
                
                # 국내외 공통으로 60일 이내로 제한
                if diff_days <= 60:
                    if is_ipo:
                        if ipo_count == 0:
                            ticker_items.append({"badge": "공모/상장", "date": event_date, "text": row['event']})
                            ipo_count += 1
                    elif is_domestic:
                        if source == 'DART':
                            if dart_count == 0:
                                ticker_items.append({"badge": "기업공시", "date": event_date, "text": row['event']})
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
                        
                # Section B (0~5일 이내)
                if 0 <= diff_days <= 5:
                    is_corp = category in ('공모청약', '신규상장', '의무보유등록해제', '파생만기', '실적발표') or source == 'DART' or '보호예수' in category
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

    # 실전플랜1 스크리닝 섹션 HTML 조립
    section_screener_html = """
    <div style="background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); border: 1px solid #a7f3d0; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.06);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; flex-wrap: wrap; gap: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #047857; display: flex; align-items: center; gap: 0.5rem; margin: 0; border: none; padding: 0;">
                📈 [실전플랜 1] 8월 3일 거래일 추천 매매 종목 <span style="font-size: 0.8rem; background: #d1fae5; color: #065f46; padding: 0.25rem 0.75rem; border-radius: 50px; font-weight: 600;">2026-07-31 종가 기준 스캔</span>
            </h3>
            <a href="reports/2026-08-01_스크리닝.html" style="text-decoration: none; color: #047857; font-size: 0.85rem; font-weight: 700; display: inline-flex; align-items: center; gap: 0.3rem; background: #ffffff; border: 1px solid #a7f3d0; padding: 0.4rem 0.9rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.1); transition: all 0.2s;">
                전체 스크리닝 리포트 보기 &rarr;
            </a>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;">
            <!-- 전략 1 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">🔵 전략 1 눌림목 (3%×3)</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">TOP 3 선택</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">★ <b>[현대힘스]</b> 13,650원 | 5일선 지지</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">★ <b>[서산]</b> 4,250원 | 13일선 지지</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">★ <b>[씨피시스템]</b> 3,865원 | 5일선 (사윗감)</li>
                </ul>
            </div>

            <!-- 전략 2 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #fef3c7; color: #92400e; border: 1px solid #fde68a; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">🟡 전략 2 매집봉 (10%×1)</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">TOP 1 선택</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">★ <b>[금호전기]</b> 4,115원 | 240일선 지지</li>
                    <li style="line-height: 1.4; margin-bottom: 0; color: #64748b;">• [아이로보틱스] 2,005원 (후보)</li>
                    <li style="line-height: 1.4; margin-bottom: 0; color: #64748b;">• [강스템바이오텍] 2,250원 (후보)</li>
                </ul>
            </div>

            <!-- 전략 3 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">🟢 전략 3 수급바닥 (10%×2)</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">TOP 2 선택</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">★ <b>[한국항공우주]</b> 127,300원 | 기관+1,761억</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">★ <b>[한화엔진]</b> 39,050원 | 기관+512억</li>
                    <li style="line-height: 1.4; margin-bottom: 0; color: #64748b;">• [한국전력], [한진칼], [하림지주] 포착</li>
                </ul>
            </div>
        </div>
    </div>
    """

    # 베타테스트 신규 4종 섹션 HTML 조립
    section_beta_html = """
    <div style="background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%); border: 2px dashed #c7d2fe; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; flex-wrap: wrap; gap: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #4338ca; display: flex; align-items: center; gap: 0.5rem; margin: 0; border: none; padding: 0;">
                🧪 임시 (베타테스트) <span style="font-size: 0.8rem; background: #e0e7ff; color: #3730a3; padding: 0.25rem 0.75rem; border-radius: 50px; font-weight: 600;">신규 로컬 파이프라인 4종 출력 시연</span>
            </h3>
            <span style="font-size: 0.8rem; color: #64748b; font-weight: 600;">⚡ 100% 로컬 연산 및 가공 추출 방식</span>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;">
            <!-- 1. B-1 증권사 리포트 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">B-1 증권사 리포트</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">목표가 상향</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">🚀 <b>[삼성E&A]</b> 실적 및 수주 상향 (미래에셋)</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">🚀 <b>[두산밥캣]</b> 대규모 관세 환입 어닝서프라이즈 (키움)</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">🚀 <b>[LIG아큐버]</b> 예상보다 빠른 턴어라운드 (미래에셋)</li>
                </ul>
            </div>

            <!-- 2. A-1 바이오/FDA 일정 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #fce7f3; color: #9d174d; border: 1px solid #fbcfe8; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">A-1 바이오/FDA 일정</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">PDUFA & 승인</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">💊 <b>[FDA 승인]</b> Oral PCSK9 Inhibitor (LDL)</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">💊 <b>[FDA 승인]</b> Gene Therapy for Sickle Cell</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">🔬 <b>[학회/임상]</b> ASCO/ESMO 학회 세션 발표</li>
                </ul>
            </div>

            <!-- 3. B-3 원자재/지정학 특보 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #fef3c7; color: #92400e; border: 1px solid #fde68a; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">B-3 원자재/지정학</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">모멘텀 가중치</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">🔥 <b>[유가/급등]</b> Brent crude tops $100/bbl</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">⚠️ <b>[지정학/공습]</b> Tankers struck off Saudi Arabia</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">🚢 <b>[해운/운임]</b> SCFI 해운 운임지수 변동 모니터링</li>
                </ul>
            </div>

            <!-- 4. A-2 아시아 매크로 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem; align-items: center;">
                    <span style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px;">A-2 아시아 매크로</span>
                    <span style="color: #d97706; font-size: 0.75rem; font-weight: 700;">중국 LPR / BOJ</span>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.85rem; color: #1e293b; display: flex; flex-direction: column; gap: 0.6rem;">
                    <li style="line-height: 1.4; margin-bottom: 0;">🇨🇳 <b>[중국]</b> 대출우대금리(LPR) 발표 및 경기부양책</li>
                    <li style="line-height: 1.4; margin-bottom: 0;">🇯🇵 <b>[일본]</b> BOJ 통화정책회의 금리 결정</li>
                </ul>
            </div>
        </div>
    </div>
    """

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
            <a href="{latest_weekly_path}" style="text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; padding: 0.85rem 1.6rem; border-radius: 50px; font-weight: 700; font-size: 0.95rem; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.25); transition: transform 0.2s ease, box-shadow 0.2s ease;" onmouseover="this.style.transform='translateY(-2px)';" onmouseout="this.style.transform='translateY(0)';">
                📊 5대 주도 섹터 위클리 브리핑 리포트 보기 &rarr;
            </a>
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
                
                {section_screener_html}
                {section_beta_html}
                {section_a_html}
                {section_b_html}

                <div class="search-filter-container">
                    <div class="search-box">
                        <input type="text" id="searchInput" placeholder="날짜 또는 리포트 키워드를 검색하세요..." oninput="filterReports()">
                    </div>
                    <div class="filter-buttons">
                        <button class="filter-btn active" onclick="filterType('all', this)">전체</button>
                        <button class="filter-btn" onclick="filterType('스크리닝', this)">📈 스크리닝</button>
                        <button class="filter-btn" onclick="filterType('장전', this)">🌅 장전</button>
                        <button class="filter-btn" onclick="filterType('장후', this)">🌆 장후</button>
                        <button class="filter-btn" onclick="filterType('주말', this)">📅 주말</button>
                    </div>
                </div>

                <div class="grid-container" id="reportsGrid">
                    <!-- 자바스크립트 동적 렌더링 -->
                </div>
                <button class="grid-toggle-btn" id="gridToggleBtn" onclick="toggleGridExpand()">
                    <span id="gridToggleLabel">▼ 더보기</span>
                </button>
            </div>
        </div>
    </main>

    <footer>
        <p>© 2026 Daily Stock News Crawler System. Powered by Gemini Pro & Antigravity AI.</p>
    </footer>

    <script>
        const reportsData = {json.dumps(report_list, ensure_ascii=False)};
        const tickerData = {json.dumps(ticker_items, ensure_ascii=False)};
        
        let currentFilter = 'all';
        let searchQuery = '';

        let gridExpanded = false;
        const COLLAPSED_HEIGHT = '800px';

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

        // --- 리포트 렌더링 로직 ---
        function renderReports() {{
            const grid = document.getElementById('reportsGrid');
            grid.innerHTML = '';
            
            const filtered = reportsData.filter(r => {{
                const matchesFilter = (currentFilter === 'all' || r.type === currentFilter);
                const matchesSearch = (r.date.includes(searchQuery) || r.type.includes(searchQuery) || r.summary.includes(searchQuery));
                return matchesFilter && matchesSearch;
            }});

            if (filtered.length === 0) {{
                grid.innerHTML = `<div class="no-results">검색 조건에 맞는 리포트가 존재하지 않습니다.</div>`;
                document.getElementById('gridToggleBtn').style.display = 'none';
                return;
            }}

            filtered.forEach(r => {{
                // 요일 구하기
                const dateObj = new Date(r.date);
                const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
                const weekday = weekdays[dateObj.getDay()];
                
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div class="card-header">
                        <span class="date-text">${{r.date}} (${{weekday}})</span>
                        <span class="badge ${{r.type}}">${{r.type}} 뉴스</span>
                    </div>
                    <p>${{r.summary}}</p>
                    <a href="${{r.html_path}}" class="view-link">
                        리포트 보기
                        <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </a>
                `;
                grid.appendChild(card);
            }});

            // 토글 상태 초기화 - 항상 접힌 상태로 시작
            gridExpanded = false;
            grid.style.maxHeight = COLLAPSED_HEIGHT;
            const btn = document.getElementById('gridToggleBtn');
            const label = document.getElementById('gridToggleLabel');
            // 스크롤 필요 없으면 버튼 숨김
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

        function filterType(type, element) {{
            currentFilter = type;
            
            // 액티브 클래스 교체
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            
            renderReports();
        }}

        function filterReports() {{
            searchQuery = document.getElementById('searchInput').value.trim();
            renderReports();
        }}

        // 초기 렌더링
        window.onload = () => {{
            renderReports();
            initTicker();
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

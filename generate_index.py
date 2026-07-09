import os
import re
import json
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
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.4);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-main: #e5e7eb;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
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
            line-height: 1.7;
            padding: 3rem 1.5rem;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 40%);
            background-attachment: fixed;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: rgba(17, 24, 39, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            padding: 3rem;
            border-radius: 24px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        }}

        .back-btn {{
            display: inline-flex;
            align-items: center;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.95rem;
            font-weight: 500;
            margin-bottom: 2.5rem;
            transition: color 0.25s ease;
            gap: 0.5rem;
        }}

        .back-btn:hover {{
            color: white;
        }}

        .back-btn svg {{
            width: 18px;
            height: 18px;
            fill: currentColor;
            transition: transform 0.25s ease;
        }}

        .back-btn:hover svg {{
            transform: translateX(-4px);
        }}

        h1 {{
            font-family: var(--font-outfit);
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(to right, #ffffff, #c7d2fe, #f472b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }}

        blockquote {{
            border-left: 4px solid var(--primary);
            padding: 0.75rem 1.25rem;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 4px 12px 12px 4px;
            color: var(--text-main);
            font-weight: 500;
            margin: 1.5rem 0 2.5rem;
        }}

        h3 {{
            font-family: var(--font-outfit);
            font-size: 1.6rem;
            color: white;
            margin-top: 3.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 2px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }}

        ul {{
            list-style: none;
            padding-left: 0;
        }}

        li {{
            margin-bottom: 2rem;
            position: relative;
            color: var(--text-muted);
            font-size: 1rem;
            line-height: 1.6;
        }}

        li a {{
            color: #818cf8;
            font-size: 1.15rem;
            font-weight: 600;
            text-decoration: none;
            transition: color 0.25s ease, border-bottom 0.25s ease;
            border-bottom: 1px solid transparent;
            display: inline-block;
            margin-bottom: 0.5rem;
        }}

        li a:hover {{
            color: #a5b4fc;
            border-bottom-color: #a5b4fc;
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
            background: linear-gradient(to right, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0) 100%);
            margin: 2.5rem 0;
        }}

        p {{
            margin-bottom: 1rem;
        }}

        footer {{
            margin-top: 5rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
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

    # reports 디렉토리 내의 모든 md 파일 검색
    files = [f for f in os.listdir(reports_dir) if f.endswith(".md")]
    
    report_list = []
    
    for filename in files:
        # 파일명 매칭: YYYY-MM-DD_유형.md
        match = re.match(r"^(\d{4}-\d{2}-\d{2})_(장전|장중|장후|주말)\.md$", filename)
        if match:
            date_str = match.group(1)
            report_type = match.group(2)
            filepath = os.path.join(reports_dir, filename)
            html_filename = filename.replace(".md", ".html")
            html_filepath = os.path.join(reports_dir, html_filename)
            
            # HTML 파일 생성
            title_str = f"{date_str} {report_type} 시황 리포트"
            try:
                convert_md_to_html(filepath, html_filepath, title_str)
            except Exception as e:
                print(f"Error compiling HTML for {filename}: {e}")
            
            # 본문 발췌(summary)는 제거하고 단순 메타데이터만 구성
            report_list.append({
                "date": date_str,
                "type": report_type,
                "html_path": f"reports/{date_str}_{report_type}.html",
                "summary": ""
            })
            
    # 날짜 내림차순, 동일 날짜 내에서는 장전 -> 장중 -> 장후 -> 주말 순 정렬
    type_order = {"장전": 1, "장중": 1.5, "장후": 2, "주말": 3}
    report_list.sort(key=lambda x: (x["date"], type_order.get(x["type"], 9)), reverse=True)

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
                
                # 캡처일 기준 과거 3일까지는 유지
                if diff_days >= -3:
                    timeline_str = str(row.get('estimated_timeline', 'N/A')).strip()
                    event_text = f"[{row.get('sector', '기타')}] {row.get('issue', 'N/A')} (시기: {timeline_str}, 수혜주: {row.get('target_stocks', 'N/A')})"
                    ticker_items.insert(0, {"badge": "VIP모멘텀", "date": event_date, "text": event_text})
                    break
        except Exception as e:
            print(f"Error loading vip db: {e}")

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
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.4);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --glow: 0 0 25px rgba(99, 102, 241, 0.25);
            --font-outfit: 'Outfit', 'Inter', sans-serif;
            --highlight-bg: rgba(239, 68, 68, 0.15);
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
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 40%);
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
            padding: 0.4rem 1rem;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            box-shadow: var(--glow);
        }}

        h1 {{
            font-family: var(--font-outfit);
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(to right, #ffffff, #c7d2fe, #f472b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
        }}

        header p {{
            color: var(--text-muted);
            font-size: 1.15rem;
            max-width: 600px;
            margin: 0 auto 1.5rem;
            line-height: 1.6;
        }}

        /* 티커 배너 컨테이너 */
        .ticker-container {{
            max-width: 800px;
            margin: 0 auto 2.5rem;
            background: rgba(17, 24, 39, 0.7);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 0 15px rgba(99, 102, 241, 0.1);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            position: relative;
            overflow: hidden;
            height: 60px; /* 고정 높이 */
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
            background: var(--primary-gradient);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            color: white;
            white-space: nowrap;
        }}

        .ticker-date {{
            color: #fbbf24;
            font-weight: 600;
            font-size: 0.85rem;
            white-space: nowrap;
        }}

        .ticker-text {{
            color: var(--text-main);
            font-size: 0.95rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 500;
        }}

        .search-filter-container {{
            width: 100%;
            background: rgba(17, 24, 39, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            padding: 1.2rem;
            border-radius: 20px;
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 1.5rem;
        }}

        .search-box {{
            position: relative;
            max-width: 400px;
            flex: 1;
        }}

        .search-box input {{
            width: 100%;
            padding: 1rem 1.5rem;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: white;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}

        .search-box input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
            background: rgba(255, 255, 255, 0.08);
        }}

        .filter-buttons {{
            display: flex;
            gap: 0.8rem;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .filter-btn {{
            padding: 0.6rem 1.5rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-main);
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.25s ease;
        }}

        .filter-btn:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.3);
        }}

        .filter-btn.active {{
            background: var(--primary);
            border-color: var(--primary);
            box-shadow: var(--glow);
        }}

        main {{
            flex: 1;
            max-width: 1400px;
            width: 100%;
            margin: 3rem auto;
            padding: 0 2rem;
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
            gap: 2rem;
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
            background: var(--accent-teal);
            border-radius: 10px;
            opacity: 0.6;
        }}

        /* 더보기/접기 버튼 */
        .grid-toggle-btn {{
            margin-top: 1.2rem;
            align-self: center;
            background: transparent;
            border: 1px solid var(--card-border);
            color: var(--text-muted);
            font-size: 0.85rem;
            font-family: var(--font-inter);
            padding: 0.5rem 1.4rem;
            border-radius: 999px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.25s ease;
        }}
        .grid-toggle-btn:hover {{
            background: var(--card-bg);
            border-color: var(--accent-teal);
            color: var(--accent-teal);
        }}

        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
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
            transform: translateY(-8px);
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 0 0 20px rgba(99, 102, 241, 0.1);
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
            font-size: 1.25rem;
            font-weight: 700;
        }}

        .badge {{
            padding: 0.35rem 0.85rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .badge.장전 {{
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        .badge.장중 {{
            background: rgba(14, 165, 233, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(14, 165, 233, 0.3);
        }}

        .badge.장후 {{
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }}

        .badge.주말 {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .card p {{
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.6;
            flex-grow: 1;
        }}

        .view-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.8rem 1.5rem;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.25s ease;
            gap: 0.5rem;
        }}

        .view-link:hover {{
            background: white;
            color: var(--bg-color);
            border-color: white;
        }}

        .view-link svg {{
            width: 16px;
            height: 16px;
            fill: currentColor;
            transition: transform 0.25s ease;
        }}

        .view-link:hover svg {{
            transform: translateX(4px);
        }}

        footer {{
            padding: 3rem 2rem;
            text-align: center;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .no-results {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 4rem;
            color: var(--text-muted);
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
        
        <div style="margin-bottom: 2.5rem;">
            <a href="schedule check/schedule.html" style="text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; background: var(--primary-gradient); color: white; border: none; padding: 0.8rem 1.5rem; border-radius: 50px; font-weight: 600; font-size: 0.95rem; box-shadow: var(--glow); transition: transform 0.2s ease, box-shadow 0.2s ease;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 25px rgba(99, 102, 241, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='var(--glow)'">
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


            <!-- 우측 뉴스 카드 그리드 및 검색 -->
            <div class="grid-wrapper">
                <div class="search-filter-container">
                    <div class="search-box">
                        <input type="text" id="searchInput" placeholder="날짜 또는 리포트 키워드를 검색하세요..." oninput="filterReports()">
                    </div>
                    <div class="filter-buttons">
                        <button class="filter-btn active" onclick="filterType('all', this)">전체</button>
                        <button class="filter-btn" onclick="filterType('장전', this)">🌅 장전</button>
                        <button class="filter-btn" onclick="filterType('장중', this)">⛅ 장중</button>
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
                const el = document.createElement('div');
                el.className = `ticker-item ${{index === 0 ? 'active' : ''}}`;
                el.id = `ticker-item-${{index}}`;
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

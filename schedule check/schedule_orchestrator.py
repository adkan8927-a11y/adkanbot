import os
import sys
import pandas as pd
from datetime import datetime

# sys path에 agents 경로 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
from dart_agent import get_dart_schedules
from macro_agent import get_macro_schedules
from rss_policy_agent import get_policy_schedules
from rss_global_agent import get_global_schedules
from static_calendar import get_static_schedules
from stock_market_agent import get_stock_market_schedules

def run_schedule_pipeline():
    print("🚀 [일정 파이프라인] 가동...")
    
    # 1. 각 에이전트로부터 일정 리스트 수집
    all_schedules = []
    
    print("📥 1. DART 공시 일정 수집 중...")
    all_schedules.extend(get_dart_schedules())
    
    print("📥 2. 거시경제 지표 수집 중...")
    all_schedules.extend(get_macro_schedules())
    
    print("📥 3. 국내 정부정책 RSS 일정 수집 중...")
    all_schedules.extend(get_policy_schedules())
    
    print("📥 4. 글로벌 컨퍼런스 RSS 일정 수집 중...")
    all_schedules.extend(get_global_schedules())
    
    print("📥 5. 정적 글로벌 일정 병합 중...")
    all_schedules.extend(get_static_schedules())
    
    print("📥 6. 증시 일정 수집 중 (공모청약/신규상장/옵션만기)...")
    all_schedules.extend(get_stock_market_schedules())
    
    print(f"📦 이번 턴에 수집 완료된 일정 수: {len(all_schedules)}건")
    
    # 2. 마스터 CSV 로드 및 병합
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "master_schedule_db.csv")
    
    new_df = pd.DataFrame(all_schedules)
    
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        except Exception as e:
            print(f"⚠️ 기존 DB 로드 실패로 신규 생성합니다: {e}")
            combined_df = new_df
    else:
        combined_df = new_df
        
    # 날짜와 이벤트가 동일한 중복 일정 정밀 디듀프
    if not combined_df.empty:
        # 공백 제거 및 문자열 변환
        combined_df['date'] = combined_df['date'].astype(str).str.strip()
        combined_df['event'] = combined_df['event'].astype(str).str.strip()
        combined_df = combined_df.drop_duplicates(subset=['date', 'event'], keep='first')
        # 날짜 정렬
        combined_df = combined_df.sort_values(by='date')
    
    # 저장
    combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"💾 마스터 데이터베이스 업데이트 완료 ({len(combined_df)}건 누적 저장)")
    
    # 3. HTML 대시보드 (schedule.html) 생성
    generate_html_dashboard(combined_df)
    
    # 4. 깃허브 자동 배포
    git_push_changes()

def generate_html_dashboard(df):
    print("🎨 스케줄 대시보드 HTML 파일 생성 중...")
    
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_dt = datetime.today()
    today_str = today_dt.strftime('%Y-%m-%d')
    
    ipo_rows = ""
    dart_rows = ""
    global_rows = ""
    
    if not df.empty:
        for _, row in df.iterrows():
            event_date = str(row['date']).strip()
            
            # 날짜 차이 계산
            try:
                target_dt = datetime.strptime(event_date, '%Y-%m-%d')
                diff_days = (target_dt.date() - today_dt.date()).days
            except:
                continue
            
            # 과거 일정 제외
            if diff_days < 0:
                continue
                
            row_class = ""
            if event_date == today_str:
                row_class = "table-highlight"
                
            category = str(row.get('category', '')).strip()
            source = str(row.get('source', '')).strip().upper()
            is_ipo = category in ('공모청약', '신규상장', '파생만기')
            is_domestic = source == 'DART' or category == '정부정책'
            
            # 국내외 공통으로 60일 이내로 제한
            if diff_days <= 60:
                if is_ipo:
                    ipo_rows += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td><span class="badge-custom">{row['category']}</span></td>
                        <td class="event-cell">{row['event']}</td>
                    </tr>
                    """
                elif is_domestic:
                    if source == 'DART':
                        dart_rows += f"""
                        <tr class="{row_class}">
                            <td class="date-cell"><strong>{event_date}</strong></td>
                            <td class="event-cell">{row['event']}</td>
                        </tr>
                        """
                    else:
                        global_rows += f"""
                        <tr class="{row_class}">
                            <td class="date-cell"><strong>{event_date}</strong></td>
                            <td><span class="badge-custom">{row['category']}</span></td>
                            <td class="event-cell">{row['event']}</td>
                        </tr>
                        """
                else:
                    global_rows += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td><span class="badge-custom">{row['category']}</span></td>
                        <td class="event-cell">{row['event']}</td>
                    </tr>
                    """
        if not ipo_rows:
            ipo_rows = "<tr><td colspan='3' style='text-align:center;'>60일 이내에 예정된 공모청약/신규상장 일정이 없습니다.</td></tr>"
        if not dart_rows:
            dart_rows = "<tr><td colspan='2' style='text-align:center;'>60일 이내에 예정된 기업 공시 일정이 없습니다.</td></tr>"
        if not global_rows:
            global_rows = "<tr><td colspan='3' style='text-align:center;'>60일 이내에 예정된 학회/매크로 일정이 없습니다.</td></tr>"
    else:
        ipo_rows = "<tr><td colspan='3' style='text-align:center;'>등록된 일정이 없습니다.</td></tr>"
        dart_rows = "<tr><td colspan='2' style='text-align:center;'>등록된 일정이 없습니다.</td></tr>"
        global_rows = "<tr><td colspan='3' style='text-align:center;'>등록된 일정이 없습니다.</td></tr>"
        
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주요 투자 일정 대시보드</title>
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
            --highlight-bg: rgba(239, 68, 68, 0.15);
            --highlight-border: rgba(239, 68, 68, 0.4);
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
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(17, 24, 39, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            padding: 3rem;
            border-radius: 24px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        }}

        header {{
            margin-bottom: 3rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        h1 {{
            font-family: var(--font-outfit);
            font-size: 2.2rem;
            font-weight: 800;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.03em;
        }}

        .meta-info {{
            font-size: 0.9rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem 1rem;
            border-radius: 99px;
            border: 1px solid var(--card-border);
        }}

        .nav-links {{
            margin-bottom: 2rem;
        }}

        .nav-btn {{
            display: inline-flex;
            align-items: center;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.95rem;
            font-weight: 500;
            transition: color 0.25s ease;
            gap: 0.5rem;
        }}

        .nav-btn:hover {{
            color: white;
        }}

        .nav-btn svg {{
            fill: currentColor;
        }}

        .table-container {{
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th, td {{
            padding: 1.2rem 1.5rem;
            border-bottom: 1px solid var(--card-border);
        }}

        th {{
            background-color: rgba(255, 255, 255, 0.03);
            font-weight: 600;
            color: var(--text-muted);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.02);
        }}

        .table-highlight {{
            background-color: var(--highlight-bg) !important;
            border-left: 4px solid #ef4444;
        }}

        .table-past {{
            opacity: 0.45;
        }}

        .date-cell {{
            white-space: nowrap;
        }}

        .badge-custom {{
            background: var(--primary-gradient);
            padding: 0.3rem 0.8rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            color: white;
            display: inline-block;
        }}

        .event-cell {{
            font-size: 0.95rem;
            color: var(--text-main);
        }}

        .source-cell {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        footer {{
            margin-top: 3rem;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            border-top: 1px solid var(--card-border);
            padding-top: 1.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav-links">
            <a href="../index.html" class="nav-btn">
                <svg viewBox="0 0 24 24" width="18" height="18">
                    <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
                </svg>
                뉴스 대시보드로 돌아가기
            </a>
        </div>
        <header>
            <h1>📅 글로벌 투자 일정 대시보드</h1>
            <div class="meta-info">최근 업데이트: {update_time}</div>
        </header>
        
        <!-- 1. 공모청약 / 신규상장 / 파생만기 일정 -->
        <div style="margin-bottom: 3rem;">
            <h2 style="font-family: var(--font-outfit); font-size: 1.3rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                📈 공모청약 · 신규상장 · 파생만기
            </h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 20%">날짜</th>
                            <th style="width: 20%">분류</th>
                            <th style="width: 60%">종목 / 내용</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ipo_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 2. 주요 기업 공시 일정 -->
        <div style="margin-bottom: 3rem;">
            <h2 style="font-family: var(--font-outfit); font-size: 1.3rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                🏢 기업 주요 공시 일정 (DART)
            </h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 20%">날짜</th>
                            <th style="width: 80%">공시 내용</th>
                        </tr>
                    </thead>
                    <tbody>
                        {dart_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 3. 학회 및 매크로 일정 -->
        <div>
            <h2 style="font-family: var(--font-outfit); font-size: 1.3rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                🌍 학회 & 미국 매크로 일정
            </h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 15%">날짜</th>
                            <th style="width: 25%">분류</th>
                            <th style="width: 60%">이벤트</th>
                        </tr>
                    </thead>
                    <tbody>
                        {global_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <footer>
            © 2026 Daily Stock News & Schedule System. Powered by Gemini & Antigravity AI.
        </footer>
    </div>
</body>
</html>
"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"✅ HTML 대시보드 빌드 완료: '{html_path}'")

def git_push_changes():
    print("🔄 [Git 배포] 변경사항 깃허브 업로드 진행...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    import subprocess
    try:
        # 변경사항 파일 add
        subprocess.run(["git", "add", "schedule check/master_schedule_db.csv", "schedule check/schedule.html"], cwd=project_root, check=True)
        
        # 커밋할 변경사항이 있는지 상태 확인
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True)
        if status_res.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Build: Auto-update investment schedule database and dashboard"], cwd=project_root, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=project_root, check=True)
            print("✅ 깃허브 원격 저장소 배포 완료!")
        else:
            print("✅ 변경사항이 없어 커밋을 건너뜁니다.")
    except Exception as e:
        print(f"❌ Git 배포 실패: {e}")

if __name__ == "__main__":
    run_schedule_pipeline()

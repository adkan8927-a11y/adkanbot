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
# from KRX_agent import get_krx_market_alerts
from lockup_agent import get_ksd_lockup_release
from ksd_corporate_agent import get_ksd_dividends
from customs_agent import get_customs_schedules
from dapa_agent import get_dapa_contracts
from assembly_agent import get_assembly_meetings

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
    
    print("📥 7. KSD 보호예수 해제 일정 수집 중...")
    all_schedules.extend(get_ksd_lockup_release())
    
    print("📥 8. KSD 배당/배당락 일정 수집 중...")
    all_schedules.extend(get_ksd_dividends())
    
    print("📥 9. 관세청 발표 예정일 계산 중...")
    all_schedules.extend(get_customs_schedules())
    
    print("📥 10. 방위사업청 계약 수주 일정 수집 중...")
    all_schedules.extend(get_dapa_contracts())
    
    print("📥 11. 국회 본회의 일정 수집 중...")
    all_schedules.extend(get_assembly_meetings())
    
    # print("📥 7. KRX 시장조치 및 추가상장 공시 수집 중...")
    # all_schedules.extend(get_krx_market_alerts())
    
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
        
    # 날짜와 이벤트가 동일한 중복 일정 정밀 디듀프 (포맷 변경에 의한 중복 흡수)
    if not combined_df.empty:
        combined_df['date'] = combined_df['date'].astype(str).str.strip()
        combined_df['event'] = combined_df['event'].astype(str).str.strip()
        
        import re
        def get_norm_key(evt):
            evt_str = str(evt)
            # 노이즈 단어 제거하여 구버전과 신버전 표기 통합 비교
            for noise in ["공시접수", "(정정)", "[기재정정]", "주요사항보고서", "결정"]:
                evt_str = evt_str.replace(noise, "")
            # 특수기호 및 공백 제거
            return re.sub(r'[^a-zA-Z0-9가-힣]', '', evt_str)
            
        combined_df['dedup_key'] = combined_df['event'].apply(get_norm_key)
        # 중복 제거 (최근 가공 룰이 적용된 행을 남기기 위해 keep='last')
        combined_df = combined_df.drop_duplicates(subset=['date', 'dedup_key'], keep='last')
        combined_df = combined_df.drop(columns=['dedup_key'])
        
        # 날짜 정렬
        combined_df = combined_df.sort_values(by='date')
        
        # 증권발행실적보고서 및 비상장 자회사/종속회사 경영사항 관련 과거 DART 일정을 마스터 DB에서 완전히 제거
        combined_df = combined_df[~((combined_df['source'] == 'DART') & (combined_df['event'].str.contains('증권발행실적보고서', na=False)))]
        combined_df = combined_df[~((combined_df['source'] == 'DART') & (combined_df['event'].str.contains('자회사의 주요경영사항|종속회사의 주요경영사항|자회사의주요경영사항|종속회사의주요경영사항', regex=True, na=False)))]
    
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
    
    # 1. schedule.html 용 (전체 리스트, 분류 유지)
    ipo_rows_all = ""
    dart_rows_all = ""
    global_rows_all = ""
    
    # 2. index.html 용 (Top 5, 분류 제거, 말머리 대괄호 포맷)
    ipo_rows_top5 = ""
    dart_rows_top5 = ""
    global_rows_top5 = ""
    
    ipo_count = 0
    dart_count = 0
    global_count = 0
    
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
            event_text = str(row.get('event', '')).strip()
            
            # 카테고리별 분기
            is_ipo = category in ('공모청약', '신규상장', '파생만기')
            is_corporate = source == 'DART' or source == '예탁결제원' or category in ('보호예수 해제', '배당/권리락')
            
            if diff_days <= 60:
                if is_ipo:
                    # schedule.html용
                    ipo_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td><span class="badge-custom">{category}</span></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                    # index.html용 (Top 5, 분류 제외)
                    if ipo_count < 5:
                        ipo_rows_top5 += f"""
                        <tr class="{row_class}">
                            <td class="date-cell"><strong>{event_date}</strong></td>
                            <td class="event-cell">{event_text}</td>
                        </tr>
                        """
                        ipo_count += 1
                elif is_corporate:
                    # schedule.html용
                    if category == '보호예수 해제':
                        badge_html = '<span class="badge-custom badge-danger">보호예수</span>'
                    elif category == '배당/권리락':
                        badge_html = '<span class="badge-custom badge-warning">배당/권리락</span>'
                    else:
                        badge_html = '<span class="badge-custom badge-info">DART공시</span>'
                        
                    dart_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td>{badge_html}</td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                    # index.html용 (Top 5, 분류 제외)
                    if dart_count < 5:
                        cat_label = category if category else "DART"
                        dart_rows_top5 += f"""
                        <tr class="{row_class}">
                            <td class="date-cell"><strong>{event_date}</strong></td>
                            <td class="event-cell">{event_text}</td>
                        </tr>
                        """
                        dart_count += 1
                else:
                    # schedule.html용
                    if category == '정부정책' or source == '국회사무처':
                        badge_html = '<span class="badge-custom badge-info">정부정책</span>'
                    elif source in ('방위사업청', '관세청') or '수출입' in event_text or '수주' in event_text:
                        badge_html = '<span class="badge-custom badge-success">수주/발표</span>'
                    else:
                        badge_html = f'<span class="badge-custom">{category}</span>'
                        
                    global_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td>{badge_html}</td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                    # index.html용 (Top 5, 분류 제외)
                    if global_count < 5:
                        global_rows_top5 += f"""
                        <tr class="{row_class}">
                            <td class="date-cell"><strong>{event_date}</strong></td>
                            <td class="event-cell">{event_text}</td>
                        </tr>
                        """
                        global_count += 1
        
        if not ipo_rows_all:
            ipo_rows_all = "<tr><td colspan='3' style='text-align:center;'>60일 이내에 예정된 공모청약/신규상장 일정이 없습니다.</td></tr>"
        if not dart_rows_all:
            dart_rows_all = "<tr><td colspan='3' style='text-align:center;'>60일 이내에 예정된 기업 공시/권리 일정이 없습니다.</td></tr>"
        if not global_rows_all:
            global_rows_all = "<tr><td colspan='3' style='text-align:center;'>60일 이내에 예정된 정책/매크로/수주 일정이 없습니다.</td></tr>"

        if not ipo_rows_top5:
            ipo_rows_top5 = "<tr><td colspan='2'>예정된 공모청약/신규상장 일정이 없습니다.</td></tr>"
        if not dart_rows_top5:
            dart_rows_top5 = "<tr><td colspan='2'>예정된 기업 공시 일정이 없습니다.</td></tr>"
        if not global_rows_top5:
            global_rows_top5 = "<tr><td colspan='2'>예정된 학회/매크로 일정이 없습니다.</td></tr>"
    else:
        ipo_rows_all = "<tr><td colspan='3' style='text-align:center;'>등록된 일정이 없습니다.</td></tr>"
        dart_rows_all = "<tr><td colspan='3' style='text-align:center;'>등록된 일정이 없습니다.</td></tr>"
        global_rows_all = "<tr><td colspan='3' style='text-align:center;'>등록된 일정이 없습니다.</td></tr>"
        
        ipo_rows_top5 = "<tr><td colspan='2'>등록된 일정이 없습니다.</td></tr>"
        dart_rows_top5 = "<tr><td colspan='2'>등록된 일정이 없습니다.</td></tr>"
        global_rows_top5 = "<tr><td colspan='2'>등록된 일정이 없습니다.</td></tr>"

    # index.html 용 VIP 돌발 일정 로드 및 HTML 생성
    vip_rows_top5 = ""
    vip_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vip_momentum_alerts.csv")
    if os.path.exists(vip_csv_path):
        try:
            df_vip = pd.read_csv(vip_csv_path)
            
            # 의미적 중복 데이터 정제 및 병합 (이중 필터링 도입)
            from sentence_transformers import SentenceTransformer, util
            import torch
            embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
            
            keep_indices = []
            seen_issues = []
            
            def is_semantic_duplicate(text1, text2, embed_model, threshold_high=0.70, threshold_low=0.55):
                try:
                    emb1 = embed_model.encode(text1, convert_to_tensor=True)
                    emb2 = embed_model.encode(text2, convert_to_tensor=True)
                    sim = float(util.cos_sim(emb1, emb2)[0][0])
                except Exception as e:
                    print(f"      ⚠️ 임베딩 유사도 연산 에러: {e}")
                    return False
                
                if sim >= threshold_high:
                    return True
                
                if sim >= threshold_low:
                    import re
                    words1 = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', text1)])
                    words2 = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', text2)])
                    common_words = words1.intersection(words2)
                    core_keywords = {'젠슨', '황', '엔비디아', '새만금', '한일', '국방', '방산', '안보', '회동', '방한', '투자', 'MOU', '골프', '정상'}
                    overlapping_cores = common_words.intersection(core_keywords)
                    
                    if len(common_words) >= 3 or len(overlapping_cores) >= 1:
                        return True
                return False
            
            for idx, row in df_vip.iterrows():
                issue_text = str(row.get('issue', '')).strip()
                if not issue_text or issue_text == "N/A":
                    continue
                
                is_dupe = False
                for seen_issue in seen_issues:
                    if is_semantic_duplicate(issue_text, seen_issue, embed_model):
                        is_dupe = True
                        break
                
                if not is_dupe:
                    keep_indices.append(idx)
                    seen_issues.append(issue_text)
            
            df_vip_cleaned = df_vip.loc[keep_indices]
            
            # 정제된 클린 데이터를 파일에 덮어씌워 영구적으로 데이터 클리닝 처리
            df_vip_cleaned.to_csv(vip_csv_path, index=False, encoding='utf-8-sig')
            
            df_vip_cleaned['date_captured'] = df_vip_cleaned['date_captured'].astype(str).str.strip()
            df_vip_cleaned = df_vip_cleaned.sort_values(by='date_captured')
            
            vip_count = 0
            for _, row in df_vip_cleaned.iterrows():
                if vip_count >= 5:
                    break
                event_date = str(row['date_captured']).strip()
                try:
                    target_dt = datetime.strptime(event_date, '%Y-%m-%d')
                    diff_days = (target_dt.date() - today_dt.date()).days
                except:
                    continue
                
                # 캡처일 기준 과거 3일까지는 유지
                if diff_days < -3:
                    continue
                
                row_class = ""
                if event_date == today_str:
                    row_class = "table-highlight"
                
                timeline_str = str(row.get('estimated_timeline', 'N/A')).strip()
                event_text = f"[{row.get('sector', '기타')}] {row.get('issue', 'N/A')} (시기: {timeline_str}, 수혜주: {row.get('target_stocks', 'N/A')})"
                
                vip_rows_top5 += f"""
                <tr class="{row_class}">
                    <td class="date-cell"><strong>{event_date}</strong></td>
                    <td class="event-cell">{event_text}</td>
                </tr>
                """
                vip_count += 1
            
            if not vip_rows_top5:
                vip_rows_top5 = "<tr><td colspan='2'>예정된 돌발 VIP 일정이 없습니다.</td></tr>"
        except Exception as e:
            vip_rows_top5 = f"<tr><td colspan='2'>돌발 일정 로드 실패: {e}</td></tr>"
    else:
        vip_rows_top5 = "<tr><td colspan='2'>등록된 돌발 VIP 일정이 없습니다.</td></tr>"
        
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

        .badge-danger {{
            background: linear-gradient(135deg, #ef4444 0%, #f43f5e 100%) !important;
        }}

        .badge-warning {{
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
            color: #0f172a !important;
        }}

        .badge-info {{
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        }}

        .badge-success {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
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
        @media (max-width: 768px) {{
            .container {{
                padding: 1.5rem 1rem;
                border: none;
                border-radius: 0;
            }}
            .table-container {{
                border: none;
                background: transparent;
                overflow-x: hidden;
            }}
            table, thead, tbody, th, td, tr {{
                display: block;
            }}
            thead {{
                display: none;
            }}
            tr {{
                margin-bottom: 1rem;
                border: 1px solid var(--card-border);
                border-radius: 12px;
                background: var(--card-bg);
                padding: 1rem;
            }}
            td {{
                border: none;
                padding: 0.4rem 0;
            }}
            .date-cell {{
                font-size: 0.95rem;
                color: var(--primary);
                margin-bottom: 0.5rem;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                padding-bottom: 0.5rem;
            }}
            .event-cell {{
                font-size: 1rem;
                margin-top: 0.5rem;
                line-height: 1.6;
            }}
            h1 {{
                font-size: 1.6rem;
                text-align: center;
            }}
            .meta-info {{
                text-align: center;
            }}
            header {{
                justify-content: center;
            }}
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
                        {ipo_rows_all}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 2. 주요 기업 공시 및 권리 일정 -->
        <div style="margin-bottom: 3rem;">
            <h2 style="font-family: var(--font-outfit); font-size: 1.3rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                🏢 국내 기업 공시 · 권리락 · 보호예수 일정
            </h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 20%">날짜</th>
                            <th style="width: 20%">분류</th>
                            <th style="width: 60%">공시 및 권리 내용</th>
                        </tr>
                    </thead>
                    <tbody>
                        {dart_rows_all}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 3. 정책 및 매크로, 수주 일정 -->
        <div>
            <h2 style="font-family: var(--font-outfit); font-size: 1.3rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                🌍 정책 · 매크로 · 수주 발표 일정
            </h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 20%">날짜</th>
                            <th style="width: 20%">분류</th>
                            <th style="width: 60%">이벤트</th>
                        </tr>
                    </thead>
                    <tbody>
                        {global_rows_all}
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
    
    # 메인 대시보드 (index.html) 내의 일정 테이블도 동기화 업데이트 (Top 5 및 VIP 일정 포함)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        main_html_path = os.path.join(project_root, "index.html")
        
        if os.path.exists(main_html_path):
            with open(main_html_path, "r", encoding="utf-8") as f:
                main_html = f.read()
            
            import re
            # 플레이스홀더 치환 (Top 5 2컬럼 구조 및 VIP 추가)
            main_html = re.sub(
                r"<!--\s*IPO_ROWS_START\s*-->.*?<!--\s*IPO_ROWS_END\s*-->",
                f"<!-- IPO_ROWS_START -->\n{ipo_rows_top5}                                <!-- IPO_ROWS_END -->",
                main_html,
                flags=re.DOTALL
            )
            main_html = re.sub(
                r"<!--\s*DART_ROWS_START\s*-->.*?<!--\s*DART_ROWS_END\s*-->",
                f"<!-- DART_ROWS_START -->\n{dart_rows_top5}                                <!-- DART_ROWS_END -->",
                main_html,
                flags=re.DOTALL
            )
            main_html = re.sub(
                r"<!--\s*GLOBAL_ROWS_START\s*-->.*?<!--\s*GLOBAL_ROWS_END\s*-->",
                f"<!-- GLOBAL_ROWS_START -->\n{global_rows_top5}                                <!-- GLOBAL_ROWS_END -->",
                main_html,
                flags=re.DOTALL
            )
            main_html = re.sub(
                r"<!--\s*VIP_ROWS_START\s*-->.*?<!--\s*VIP_ROWS_END\s*-->",
                f"<!-- VIP_ROWS_START -->\n{vip_rows_top5}                                <!-- VIP_ROWS_END -->",
                main_html,
                flags=re.DOTALL
            )
            
            with open(main_html_path, "w", encoding="utf-8") as f:
                f.write(main_html)
            print(f"✅ 메인 대시보드 index.html 일정 동기화 완료!")
    except Exception as me:
        print(f"⚠️ 메인 대시보드 index.html 동기화 실패: {me}")

def git_push_changes():
    print("🔄 [Git 배포] 변경사항 깃허브 업로드 진행...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    import subprocess
    try:
        # 변경사항 파일 add (index.html 도 추가)
        subprocess.run(["git", "add", "schedule check/master_schedule_db.csv", "schedule check/schedule.html", "index.html"], cwd=project_root, check=True)
        
        # 커밋할 변경사항이 있는지 상태 확인
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True)
        if status_res.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Build: Auto-update investment schedule database and dashboard"], cwd=project_root, check=True)
            try:
                print("⬇️ 원격 저장소 변경사항 병합 중...")
                subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=project_root, check=True)
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Git Pull 실패 (수동 충돌 해결 필요): {e}")
            subprocess.run(["git", "push", "origin", "main"], cwd=project_root, check=True)
            print("✅ 깃허브 원격 저장소 배포 완료!")
        else:
            print("✅ 변경사항이 없어 커밋을 건너뜁니다.")
    except Exception as e:
        print(f"❌ Git 배포 실패: {e}")

if __name__ == "__main__":
    run_schedule_pipeline()

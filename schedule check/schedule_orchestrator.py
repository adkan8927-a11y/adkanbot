import os
import sys
import pandas as pd
from datetime import datetime

# sys path에 agents 경로 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
from dart_agent import get_dart_schedules
from fred_macro_agent import get_fred_macro_schedules
from rss_policy_agent import get_policy_schedules
from rss_global_agent import get_global_schedules
from static_calendar import get_static_schedules
from stock_market_agent import get_stock_market_schedules
# from KRX_agent import get_krx_market_alerts
from pdf_lockup_agent import get_pdf_lockup_schedules
from cb_agent import get_historical_cb_overhang
from customs_agent import get_customs_schedules
from dapa_agent import get_dapa_contracts
from earnings_agent import get_earnings_schedule

def run_schedule_pipeline():
    print("🚀 [일정 파이프라인] 가동...")
    
    # 1. 각 에이전트로부터 일정 리스트 수집
    all_schedules = []
    
    print("📥 1. DART 공시 일정 수집 중...")
    all_schedules.extend(get_dart_schedules())
    
    print("📥 2. FRED 거시경제 지표 수집 중...")
    all_schedules.extend(get_fred_macro_schedules())
    
    print("📥 3. 국내 정부정책 RSS 일정 수집 중...")
    all_schedules.extend(get_policy_schedules())
    
    print("📥 4. 글로벌 컨퍼런스 RSS 일정 수집 중...")
    all_schedules.extend(get_global_schedules())
    
    print("📥 5. 정적 글로벌 일정 병합 중...")
    all_schedules.extend(get_static_schedules())
    
    print("📥 6. 증시 일정 수집 중 (공모청약/신규상장/옵션만기)...")
    all_schedules.extend(get_stock_market_schedules())
    
    print("📥 7. KSD 보호예수 해제 일정 수집 중 (로컬 PDF 정적 데이터)...")
    all_schedules.extend(get_pdf_lockup_schedules())
    
    print("📥 7-1. DART 1년 전 발행 CB/BW 오버행(잠재매도) 수집 중...")
    all_schedules.extend(get_historical_cb_overhang())
    
    print("📥 8. 관세청 발표 예정일 계산 중...")
    all_schedules.extend(get_customs_schedules())
    
    print("📥 9. 방위사업청 계약 수주 일정 수집 중...")
    all_schedules.extend(get_dapa_contracts())
    
    print("📥 10. 빅테크 실적발표 일정 수집 중...")
    all_schedules.extend(get_earnings_schedule())

    
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
    
    # 1. schedule.html 용 (6분할)
    macro_rows_all = ""
    policy_rows_all = ""
    conference_rows_all = ""
    dart_rows_all = ""
    ipo_rows_all = ""
    overhang_rows_all = ""
    
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
            
            # [강제 규칙] 단순 당일 공시접수 건은 대시보드 표시에서 제외 (미래 일정 추적용으로 CSV 내부 데이터로만 보관)
            if source == 'DART' and '공시접수' in event_text:
                continue
            
            if diff_days <= 60:
                if category in ('거시 지표', '거시 일정') or 'FOMC' in event_text.upper() or source == 'FRED API':
                    macro_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                # 2. 국내 정책 및 모멘텀 (파생만기 포함)
                elif category in ('정부정책', '파생만기') or source in ('관세청', '방위사업청', '국회사무처') or '옵션만기' in event_text:
                    policy_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                # 3. 글로벌 학회 및 컨퍼런스
                elif category in ('해외학회', '글로벌 일정') or source in ('GOOGLE ALERTS', 'PR NEWSWIRE'):
                    conference_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                # 5. 공모청약 및 신규상장
                elif category in ('공모청약', '신규상장'):
                    ipo_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                # 6. 리스크 및 잠재 매도 (오버행, 보호예수)
                elif category in ('보호예수 해제', '잠재매도(오버행)') or 'CB/BW' in event_text:
                    overhang_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """
                # 4. 기타 기업 핵심 공시 (DART, 배당 등)
                else:
                    dart_rows_all += f"""
                    <tr class="{row_class}">
                        <td class="date-cell"><strong>{event_date}</strong></td>
                        <td class="event-cell">{event_text}</td>
                    </tr>
                    """

        # 빈 데이터 처리
        empty_tr = "<tr><td colspan='2' style='text-align:center; color: var(--text-muted);'>60일 이내에 예정된 일정이 없습니다.</td></tr>"
        if not macro_rows_all: macro_rows_all = empty_tr
        if not policy_rows_all: policy_rows_all = empty_tr
        if not conference_rows_all: conference_rows_all = empty_tr
        if not dart_rows_all: dart_rows_all = empty_tr
        if not ipo_rows_all: ipo_rows_all = empty_tr
        if not overhang_rows_all: overhang_rows_all = empty_tr
    else:
        empty_tr = "<tr><td colspan='2' style='text-align:center; color: var(--text-muted);'>등록된 일정이 없습니다.</td></tr>"
        macro_rows_all = empty_tr
        policy_rows_all = empty_tr
        conference_rows_all = empty_tr
        dart_rows_all = empty_tr
        ipo_rows_all = empty_tr
        overhang_rows_all = empty_tr

    # index.html 용 VIP 돌발 일정 로드 및 HTML 생성
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
            
            # index.html 용 VIP 돌발 일정 로드 및 HTML 생성
            vip_hero_html = ""
            
            df_vip_cleaned['date_captured'] = df_vip_cleaned['date_captured'].astype(str).str.strip()
            df_vip_cleaned = df_vip_cleaned.sort_values(by='date_captured', ascending=False)
            
            for _, row in df_vip_cleaned.iterrows():
                event_date = str(row['date_captured']).strip()
                timeline_str = str(row.get('estimated_timeline', 'N/A')).strip()
                
                # 구체적 일정이 지정된 최신 1개만 노출
                if re.search(r'\d+월|\d+일', timeline_str):
                    issue = str(row.get('issue', 'N/A')).strip()
                    sector = str(row.get('sector', '기타')).strip()
                    stocks = str(row.get('target_stocks', '')).strip()
                    vip_link = str(row.get('link', '')).strip()
                    
                    card_content = f"""
                    <div style="background: linear-gradient(135deg, rgba(255,0,128,0.1) 0%, rgba(99,102,241,0.1) 100%); border: 1px solid rgba(255,0,128,0.3); border-radius: 20px; padding: 2.5rem; margin-bottom: 3rem; text-align: center; box-shadow: 0 15px 40px rgba(0,0,0,0.3), inset 0 0 20px rgba(255,0,128,0.05); position: relative; overflow: hidden;">
                        <div style="position: absolute; top: -10px; right: -10px; font-size: 8rem; opacity: 0.05; transform: rotate(15deg);">🚀</div>
                        <span style="background: linear-gradient(90deg, #ff0080, #7928ca); color: white; padding: 0.4rem 1rem; border-radius: 30px; font-weight: 800; font-size: 0.9rem; letter-spacing: 0.1em; display: inline-block; margin-bottom: 1.5rem; box-shadow: 0 4px 15px rgba(255,0,128,0.4);">🔥 VIP 핫 모멘텀 ({event_date})</span>
                        <h2 style="font-size: 2rem; font-weight: 800; color: #f8fafc; margin-bottom: 1rem; line-height: 1.4;">[{sector}] {issue}</h2>
                        <div style="display: flex; justify-content: center; gap: 2rem; color: #cbd5e1; font-size: 1.1rem; margin-bottom: 1.5rem; font-weight: 500;">
                            <span>🗓️ 시기: <strong style="color: #38bdf8;">{timeline_str}</strong></span>
                            <span>🎯 수혜주: <strong style="color: #10b981;">{stocks}</strong></span>
                        </div>
                    """
                    if vip_link and vip_link != 'nan':
                        card_content += f'<a href="{vip_link}" target="_blank" style="display: inline-block; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; text-decoration: none; padding: 0.8rem 2rem; border-radius: 50px; font-weight: 600; transition: all 0.2s;" onmouseover="this.style.background=\'rgba(255,255,255,0.2)\'" onmouseout="this.style.background=\'rgba(255,255,255,0.1)\'">관련 뉴스 원문 보기 &rarr;</a>'
                    
                    card_content += "</div>"
                    vip_hero_html = card_content
                    break
            
            if not vip_hero_html:
                vip_hero_html = ""
        except Exception as e:
            vip_hero_html = ""
    else:
        vip_hero_html = ""
        
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
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(17, 24, 39, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            padding: 2.5rem;
            border-radius: 24px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 2rem;
            margin-bottom: 2rem;
        }}

        .grid-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            height: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}

        .grid-card h2 {{
            font-family: var(--font-outfit);
            font-size: 1.25rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-shrink: 0;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 0.8rem;
        }}

        .table-wrapper {{
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .table-wrapper::-webkit-scrollbar {{
            width: 6px;
        }}
        .table-wrapper::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
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

        .event-cell {{
            font-size: 0.95rem;
            color: var(--text-main);
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
        
        {vip_hero_html}
        
        <!-- 6분할 그리드 대시보드 레이아웃 시작 -->
        <div class="dashboard-grid">
            
            <!-- 1. 매크로 및 글로벌 이벤트 -->
            <div class="grid-card">
                <h2>🇺🇸 매크로 & 글로벌 주요 이벤트</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%">날짜</th>
                                <th style="width: 75%">이벤트 / 공시 내용</th>
                            </tr>
                        </thead>
                        <tbody>
                            {macro_rows_all}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 2. 국내 정책 및 모멘텀 -->
            <div class="grid-card">
                <h2>🇰🇷 국내 정책 및 모멘텀 (파생만기)</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%">날짜</th>
                                <th style="width: 75%">이벤트 / 공시 내용</th>
                            </tr>
                        </thead>
                        <tbody>
                            {policy_rows_all}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 3. 글로벌 학회 및 컨퍼런스 -->
            <div class="grid-card">
                <h2>🌍 글로벌 학회 & 컨퍼런스</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%">날짜</th>
                                <th style="width: 75%">이벤트 / 공시 내용</th>
                            </tr>
                        </thead>
                        <tbody>
                            {conference_rows_all}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 4. 기업 핵심 공시 -->
            <div class="grid-card">
                <h2>🏢 기업 핵심 공시 (DART)</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%">날짜</th>
                                <th style="width: 75%">이벤트 / 공시 내용</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dart_rows_all}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 5. 공모청약 및 신규상장 -->
            <div class="grid-card">
                <h2>🚀 공모청약 & 신규상장</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%">날짜</th>
                                <th style="width: 75%">이벤트 / 공시 내용</th>
                            </tr>
                        </thead>
                        <tbody>
                            {ipo_rows_all}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 6. 잠재 매도 리스크 -->
            <div class="grid-card" style="border-color: rgba(239, 68, 68, 0.4); box-shadow: 0 10px 30px rgba(239, 68, 68, 0.1);">
                <h2>🚨 잠재 매도 리스크 (Overhang)</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%">날짜</th>
                                <th style="width: 75%">이벤트 / 공시 내용</th>
                            </tr>
                        </thead>
                        <tbody>
                            {overhang_rows_all}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
        <!-- 6분할 그리드 끝 -->

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
    
    # 메인 대시보드 (index.html) 업데이트는 GitHub Actions (generate_index.py) 로 역할을 위임하여 충돌을 방지합니다.

def git_push_changes():
    print("🔄 [Git 배포] 변경사항 깃허브 업로드 진행...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    import subprocess
    try:
        # 변경사항 파일 add (index.html은 제외하여 프론트엔드/백엔드 충돌 원천 차단)
        subprocess.run(["git", "add", "schedule check/master_schedule_db.csv", "schedule check/vip_momentum_alerts.csv", "schedule check/schedule.html"], cwd=project_root, check=True)
        
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

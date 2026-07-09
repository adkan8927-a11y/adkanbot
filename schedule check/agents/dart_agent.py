import OpenDartReader
import re
from datetime import datetime, timedelta

def clean_html(raw_html):
    """HTML/XML 태그 제거 및 공백 정제"""
    if not raw_html:
        return ""
    return re.sub(r'<[^<]+>', '\n', raw_html)

def format_event_name(corp_name, report_nm, event_type=""):
    """
    공시 이벤트명을 정제:
    1. '기재정정' 문구를 맨 뒤의 '(정정)'으로 이동.
    2. '유상증자결정', '무상증자결정', '회사합병결정' -> '결정' 단어 제거.
    3. '주요사항보고서(' 및 ')' 제거.
    """
    is_rectified = '기재정정' in report_nm
    
    # 기재정정 관련 수식어 제거
    clean_nm = report_nm.replace('[기재정정]', '').replace('(기재정정)', '').replace('기재정정', '')
    
    # 주요사항보고서 괄호 제거
    clean_nm = clean_nm.replace('주요사항보고서(', '').replace(')', '')
    
    # '결정' 단어 제거
    clean_nm = clean_nm.replace('유상증자결정', '유상증자').replace('무상증자결정', '무상증자').replace('회사합병결정', '회사합병')
    clean_nm = clean_nm.replace('결정', '')
    
    # 앞뒤 공백 및 더블 스페이스 정리
    clean_nm = re.sub(r'\s+', ' ', clean_nm).strip()
    
    if event_type:
        event_title = f"[{corp_name}] {clean_nm} {event_type}".strip()
    else:
        event_title = f"[{corp_name}] {clean_nm} 공시접수".strip()
        
    event_title = re.sub(r'\s+', ' ', event_title)
    
    if is_rectified:
        event_title += " (정정)"
        
    return event_title

def get_prev_business_day(date_str):
    """신주배정기준일 기준 1영업일 전(권리락일) 계산 (주말 회피)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    while True:
        dt = dt - timedelta(days=1)
        if dt.weekday() < 5:  # 0~4: 월~금
            break
    return dt.strftime('%Y-%m-%d')

def parse_date_from_text(text):
    """텍스트에서 다양한 형식의 YYYY-MM-DD 날짜 추출 및 변환"""
    # YYYY년 MM월 DD일 형식
    m1 = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', text)
    if m1:
        return f"{m1.group(1)}-{int(m1.group(2)):02d}-{int(m1.group(3)):02d}"
    # YYYY-MM-DD 또는 YYYY.MM.DD 형식
    m2 = re.search(r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', text)
    if m2:
        return f"{m2.group(1)}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
    return None

def extract_dates_from_report(doc_text, report_nm):
    """정제된 공시 보고서 텍스트에서 중요 일정 날짜 추출"""
    text_lines = [line.strip() for line in doc_text.split('\n') if line.strip()]
    dates = {}
    
    is_capital = '증자' in report_nm
    is_merger = '합병' in report_nm
    is_earnings = any(kw in report_nm for kw in ['영업실적발표예고', '잠정실적발표예고', '실적발표 예정', '실적발표예고'])
    
    for i, line in enumerate(text_lines):
        # 1. 유/무상증자결정 타겟
        if is_capital:
            if '신주배정기준일' in line:
                for offset in range(1, 6):
                    if i + offset < len(text_lines):
                        d = parse_date_from_text(text_lines[i + offset])
                        if d:
                            dates['신주배정기준일'] = d
                            break
            elif '상장 예정일' in line or '상장예정일' in line:
                for offset in range(1, 6):
                    if i + offset < len(text_lines):
                        d = parse_date_from_text(text_lines[i + offset])
                        if d:
                            dates['신주상장예정일'] = d
                            break
                            
        # 2. 합병결정 타겟
        elif is_merger:
            if '합병기일' in line:
                for offset in range(1, 6):
                    if i + offset < len(text_lines):
                        d = parse_date_from_text(text_lines[i + offset])
                        if d:
                            dates['합병기일'] = d
                            break
            elif '상장 예정일' in line or '상장예정일' in line:
                for offset in range(1, 6):
                    if i + offset < len(text_lines):
                        d = parse_date_from_text(text_lines[i + offset])
                        if d:
                            dates['신주상장예정일'] = d
                            break
                            
        # 3. 실적발표 예고 타겟
        elif is_earnings:
            if any(kw in line for kw in ['예정일', '일시', '개최일자', '발표일', '예정 일자']):
                for offset in range(0, 6):
                    if i + offset < len(text_lines):
                        d = parse_date_from_text(text_lines[i + offset])
                        if d:
                            dates['실적발표예정일'] = d
                            break
                if '실적발표예정일' in dates:
                    break
                    
    return dates

def get_dart_schedules():
    """DART 공시 일정 수집 및 핵심 미래 일정 정밀 추출"""
    print("📥 DART 공시 일정 및 미래 투자 일정 분석 중...")
    api_key = '63cfc7d9c10a4c87a2e735d31f8ff4c4351207de'
    
    try:
        dart = OpenDartReader(api_key)
        today_dt = datetime.today()
        
        # 주말 대응 (토요일이면 어제 금요일, 일요일이면 그저께 금요일)
        if today_dt.weekday() == 5: # 토요일
            query_date = (today_dt - timedelta(days=1)).strftime('%Y%m%d')
        elif today_dt.weekday() == 6: # 일요일
            query_date = (today_dt - timedelta(days=2)).strftime('%Y%m%d')
        else:
            query_date = today_dt.strftime('%Y%m%d')
            
        df = dart.list(start=query_date, end=query_date)
        schedules = []
        
        if df is not None and not df.empty:
            # 유가증권(Y) 및 코스닥(K) 상장사만 필터링
            df = df[df['corp_cls'].isin(['Y', 'K'])]
            
            target_keywords = '실적|증자|소각|합병|분할|단기과열|투자경고|투자주의|거래정지|추가상장|불성실|상장폐지'
            important_reports = df[df['report_nm'].str.contains(target_keywords, regex=True, na=False)]
            
            for _, row in important_reports.iterrows():
                corp_name = str(row['corp_name']).strip()
                report_nm = str(row['report_nm']).strip()
                rcept_no = str(row['rcept_no']).strip()
                rcept_dt_str = str(row['rcept_dt']).strip()
                
                # 증권발행실적보고서,단일판매는 수집 차단
                if any(kw in report_nm for kw in ['증권발행실적보고서', '단일판매']):
                    continue
                    
                # 비상장 자회사/종속회사의 주요경영사항 공시는 수집 차단 (노이즈 방지)
                if any(kw in report_nm for kw in ['자회사의 주요경영사항', '종속회사의 주요경영사항', '자회사의주요경영사항', '종속회사의주요경영사항']):
                    continue
                
                # 접수일 포맷 (YYYY-MM-DD)
                rcept_dt_formatted = datetime.strptime(rcept_dt_str, '%Y%m%d').strftime('%Y-%m-%d')
                
                # 유/무상증자결정 및 합병결정 공시의 경우 상세 일정 파싱 시도
                is_target_report = any(kw in report_nm for kw in ['유상증자결정', '무상증자결정', '합병결정', '영업실적발표예고', '잠정실적발표예고', '실적발표 예정', '실적발표예고'])
                if is_target_report:
                    print(f"  🔍 DART 상세 파싱 대상 포착: [{corp_name}] {report_nm}")
                    target_schedules = []
                    try:
                        doc_raw = dart.document(rcept_no)
                        if doc_raw:
                            doc_text = clean_html(doc_raw)
                            extracted = extract_dates_from_report(doc_text, report_nm)
                            
                            # 미래 일정 등록
                            for event_type, date_val in extracted.items():
                                try:
                                    target_dt = datetime.strptime(date_val, '%Y-%m-%d')
                                    # 과거 일정이 아닌 경우에만 등록
                                    if target_dt.date() >= today_dt.date():
                                        cat = "실적발표" if "실적발표" in event_type else "경제 일반"
                                        target_schedules.append({
                                            "date": date_val,
                                            "category": cat,
                                            "event": format_event_name(corp_name, report_nm, event_type),
                                            "source": "DART"
                                        })
                                        print(f"    → 미래 일정 추출 성공: {date_val} | {event_type}")
                                        
                                        # 신주배정기준일인 경우 권리락일(1영업일 전)도 자동 계산하여 캘린더 주입
                                        if event_type == '신주배정기준일':
                                            prev_biz_date = get_prev_business_day(date_val)
                                            prev_biz_dt = datetime.strptime(prev_biz_date, '%Y-%m-%d')
                                            if prev_biz_dt.date() >= today_dt.date():
                                                target_schedules.append({
                                                    "date": prev_biz_date,
                                                    "category": "배당/권리락",
                                                    "event": f"[권리락] {format_event_name(corp_name, report_nm, '권리락')}",
                                                    "source": "DART"
                                                })
                                                print(f"    → 권리락일 역산 주입 성공: {prev_biz_date} | 권리락")
                                except ValueError:
                                    continue
                    except Exception as doc_err:
                        print(f"  ⚠️ [{corp_name}] 본문 일정 파싱 중 오류 (기본 일정만 사용): {doc_err}")
                    
                    # 미래 일정이 정상 추출되었다면 그것만 등록, 실패했다면 백업으로 기본 공시접수 알림 등록
                    if target_schedules:
                        schedules.extend(target_schedules)
                    else:
                        schedules.append({
                            "date": rcept_dt_formatted,
                            "category": "경제 일반",
                            "event": format_event_name(corp_name, report_nm),
                            "source": "DART"
                        })
                else:
                    # 상세 파싱 대상이 아닌 일반 공시(실적 등)는 즉시 기본 접수 알림 추가
                    schedules.append({
                        "date": rcept_dt_formatted,
                        "category": "경제 일반",
                        "event": format_event_name(corp_name, report_nm),
                        "source": "DART"
                    })
                        
        return schedules
    except Exception as e:
        print(f"❌ DART 수집 에러: {e}")
        return []

if __name__ == "__main__":
    # 최근 특정 일자의 샘플을 통한 로직 강제 검증 테스트 데모
    import sys
    
    # 2026-06-25의 '레몬' 유상증자(20260625000509) 테스트
    print("\n--- 1. 레몬 유상증자 샘플 데이터 단독 테스트 ---")
    try:
        dart = OpenDartReader('63cfc7d9c10a4c87a2e735d31f8ff4c4351207de')
        doc = dart.document('20260625000509')
        if doc:
            doc_text = clean_html(doc)
            res = extract_dates_from_report(doc_text, '주요사항보고서(유상증자결정)')
            print("레몬 유상증자 추출 결과:", res)
    except Exception as te:
        print("샘플 테스트 실패:", te)
        
    print("\n--- 2. 오늘의 DART 수집 테스트 ---")
    res_schedules = get_dart_schedules()
    print(f"\n총 {len(res_schedules)}개 일정 반환됨:")
    for s in res_schedules:
        print(f"  {s['date']} | {s['category']} | {s['event']}")

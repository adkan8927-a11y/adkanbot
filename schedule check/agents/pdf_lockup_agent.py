import os
import glob
import pdfplumber
from datetime import datetime

def get_pdf_lockup_schedules():
    print("🔐 [KSD 보호예수 에이전트] 로컬 PDF 정적 데이터 스캔 중...")
    
    # 1. schedule check 최상위 폴더 및 상위 폴더에서 의무보유등록 관련된 pdf 파일 찾기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(parent_dir)
    
    # KSD 보도자료 파일 패턴 검색 (예: *의무보유등록*해제*.pdf)
    pdf_files = glob.glob(os.path.join(project_root, "*의무보유등록*해제*.pdf"))
    if not pdf_files:
        print("  ℹ️ 보호예수 해제 안내 PDF 파일을 찾을 수 없습니다. (매월 말 수동 다운로드 필요)")
        return []
        
    # 가장 최근에 다운로드된 파일 선택 (수정 시간 기준)
    latest_pdf = max(pdf_files, key=os.path.getmtime)
    print(f"  ▶ 발견된 PDF 파일: {os.path.basename(latest_pdf)}")
    
    schedules = []
    current_year = datetime.today().year
    
    try:
        with pdfplumber.open(latest_pdf) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue
                    
                for table in tables:
                    # 표의 헤더가 있는지 확인
                    # 예탁원 표 양식: ['해제일', '종 목 명', '해제주식수', '비율(%)*']
                    if not table or len(table[0]) < 3:
                        continue
                        
                    header_row = [str(x).replace('\n', '').strip() for x in table[0] if x]
                    if '해제일' not in header_row or '종 목 명' not in header_row:
                        continue
                    
                    # 데이터 행 파싱
                    for row in table[1:]:
                        if not row or len(row) < 3:
                            continue
                            
                        raw_date = str(row[0]).strip()
                        company = str(row[1]).replace('\n', ' ').strip()
                        qty = str(row[2]).replace('\n', '').strip()
                        ratio = str(row[3]).replace('\n', '').strip() if len(row) > 3 else "?"
                        
                        # 날짜 파싱 (예: "7.11." -> "2026-07-11")
                        if raw_date and raw_date.count('.') >= 1:
                            parts = raw_date.split('.')
                            if len(parts) >= 2:
                                month = parts[0].strip()
                                day = parts[1].strip()
                                if month.isdigit() and day.isdigit():
                                    date_str = f"{current_year}-{int(month):02d}-{int(day):02d}"
                                    
                                    # 이벤트 문자열 생성
                                    event_text = f"[보호예수] {company} 의무보유 해제 ({qty} 주, {ratio}%)"
                                    
                                    schedules.append({
                                        "date": date_str,
                                        "category": "보호예수 해제",
                                        "event": event_text,
                                        "source": "예탁결제원(PDF)"
                                    })
                                    
        print(f"  🎉 PDF 파싱 완료: 총 {len(schedules)}건의 보호예수 해제 일정 추출 성공!")
        return schedules
        
    except Exception as e:
        print(f"  ⚠️ PDF 파싱 중 오류 발생: {e}")
        return []

if __name__ == "__main__":
    res = get_pdf_lockup_schedules()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

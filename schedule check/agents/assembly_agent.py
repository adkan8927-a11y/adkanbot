import requests
from datetime import datetime

def get_assembly_meetings():
    print("🏛️ [국회 에이전트] 국회 본회의 일정 수집 중...")
    
    # 국회 본회의 일정 OpenAPI URL
    url = "https://open.assembly.go.kr/portal/openapi/nekcaiymatialqlxr"
    
    params = {
        'Type': 'json',
        'pIndex': '1',
        'pSize': '50',
        'UNIT_CD': '100022'  # 제22대 국회 코드
    }
    
    schedules = []
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"  ⚠️ 국회 API 응답 실패 (Status Code: {response.status_code}).")
            return []
            
        data = response.json()
        
        # 에러 체크
        if "RESULT" in data and "CODE" in data["RESULT"]:
            code = data["RESULT"]["CODE"]
            msg = data["RESULT"]["MESSAGE"]
            # API 키 오류나 서비스 오류 시
            if code.startswith("ERROR"):
                print(f"  ⚠️ 국회 API 에러 반환: CODE={code}, MSG={msg}")
                return []
                
        # 서비스 키워드로 JSON 키 매핑
        # 국회 API 구조는 {"nekcaiymatialqlxr": [{"head": [...]}, {"row": [...]}]}
        service_key_name = "nekcaiymatialqlxr"
        if service_key_name not in data:
            print("  ℹ️ 국회 본회의 신규 일정이 존재하지 않습니다.")
            return []
            
        rows = data[service_key_name][1]["row"]
        today_dt = datetime.today()
        
        for row in rows:
            title = row.get("TITLE", "").strip()            # 안건/회의명
            meet_date_raw = row.get("MEETTING_DATE", "").strip() # 회의일자 (YYYY-MM-DD)
            session_nm = row.get("MEETINGSESSION", "").strip() # 회기 (예: 제415회)
            cha_nm = row.get("CHA", "").strip()             # 차수 (예: 제1차)
            
            if not title or not meet_date_raw:
                continue
                
            try:
                meet_dt = datetime.strptime(meet_date_raw, '%Y-%m-%d')
                # 미래 일정만 등록
                if meet_dt.date() >= today_dt.date():
                    event_text = f"[국회] {session_nm} {cha_nm} 본회의 ({title[:25]}...)"
                    
                    schedules.append({
                        "date": meet_date_raw,
                        "category": "정부정책",
                        "event": event_text,
                        "source": "국회사무처"
                    })
            except ValueError:
                continue
                
        # 중복 제거 및 정렬
        schedules = sorted(schedules, key=lambda x: x['date'])
        print(f"  🎉 국회 본회의 일정 {len(schedules)}건 수집 완료!")
        return schedules
        
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ 국회 API 통신 장애: {e}")
        return []
    except Exception as ex:
        print(f"  ⚠️ 국회 API 파싱 중 예상치 못한 오류: {ex}")
        return []

if __name__ == "__main__":
    res = get_assembly_meetings()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

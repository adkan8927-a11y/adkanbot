import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

DAPA_API_KEY = "5d5e6d63fb73bc35c5e8e727ebd98ad01c1fd87293666e86a1f0676d35b6c7b6"

def get_dapa_contracts():
    print("🔫 [방사청 에이전트] 방위사업청 계약 수주 현황 수집 중...")
    
    # 방위사업청 국외계약 정보 오픈 API URL
    url = "https://apis.data.go.kr/1690000/CntrctInfoService/getOutnatnCntrctInfoList"
    
    params = {
        'serviceKey': DAPA_API_KEY,
        'pageNo': '1',
        'numOfRows': '100',
        'resultType': 'xml'
    }
    
    schedules = []
    
    # 주요 상장 방산 기업 목록
    defense_corps = {
        "한화에어로스페이스", "한화에어로", "LIG넥스원", "LIG넥스", "현대로템", "로템", 
        "한국항공우주", "KAI", "한화시스템", "풍산", "한화오션"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"  ⚠️ 방사청 API 응답 실패 (Status Code: {response.status_code}). 인증키 활성화 대기 중일 수 있습니다.")
            return []
            
        root = ET.fromstring(response.content)
        
        # resultCode 검사
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text != '00':
            result_msg = root.find('.//resultMsg')
            msg_text = result_msg.text if result_msg is not None else "Unknown Error"
            print(f"  ⚠️ 방사청 API 에러 반환: CODE={result_code.text}, MSG={msg_text}")
            return []
            
        items = root.findall('.//item')
        if not items:
            print("  ℹ️ 방위사업청 최근 계약 내역이 존재하지 않습니다.")
            return []
            
        today_dt = datetime.today()
        
        for item in items:
            cntrct_date_raw = item.findtext('cntrctDate', default='').strip()   # 계약일자 (YYYYMMDD)
            cntrct_divs = item.findtext('cntrctDivs', default='').strip()       # 계약구분 (물품, 용역 등)
            cntrct_entrps = item.findtext('cntrctEntrpsNm', default='').strip() # 계약업체명
            cntrct_no = item.findtext('cntrctNo', default='').strip()           # 계약번호
            
            # 계약업체명에 주요 방산 기업이 포함되어 있는지 필터링
            target_corp = None
            for corp in defense_corps:
                if corp in cntrct_entrps:
                    target_corp = corp
                    break
                    
            if not target_corp or not cntrct_date_raw:
                continue
                
            # 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
            if len(cntrct_date_raw) == 8:
                cntrct_date = f"{cntrct_date_raw[:4]}-{cntrct_date_raw[4:6]}-{cntrct_date_raw[6:]}"
            else:
                continue
                
            event_text = f"[방산수주] {target_corp} 국외계약 체결 ({cntrct_divs}) - {cntrct_no}"
            
            schedules.append({
                "date": cntrct_date,
                "category": "경제 일반",
                "event": event_text,
                "source": "방위사업청"
            })
            
        print(f"  🎉 방산 수주 계약 일정 {len(schedules)}건 수집 완료!")
        return schedules
        
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ 방사청 API 통신 장애: {e}")
        return []
    except ET.ParseError:
        print("  ⚠️ XML 파싱 실패. 공공데이터포털 서버 일시 장애 또는 API 키 미승인 상태일 수 있습니다.")
        return []
    except Exception as ex:
        print(f"  ⚠️ 예상치 못한 오류: {ex}")
        return []

if __name__ == "__main__":
    res = get_dapa_contracts()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

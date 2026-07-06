import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

KSD_API_KEY = "5d5e6d63fb73bc35c5e8e727ebd98ad01c1fd87293666e86a1f0676d35b6c7b6"

def get_ksd_dividends():
    print("💰 [KSD 배당 에이전트] 배당 및 배당락 일정 수집 중...")
    
    today_dt = datetime.today()
    
    # 공공데이터포털 KSD 주식정보서비스 배당분배금내역 정보 API
    url = "https://apis.data.go.kr/B552481/service/StockSvc/getDivInfo"
    
    params = {
        'serviceKey': KSD_API_KEY,
        'pageNo': '1',
        'numOfRows': '100',
        'basDt': today_dt.strftime('%Y%m%d') # 오늘 기준일
    }
    
    schedules = []
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"  ⚠️ KSD 배당 API 응답 실패 (Status Code: {response.status_code}). 인증키 활성화 대기 중일 수 있습니다.")
            return []
            
        root = ET.fromstring(response.content)
        
        # resultCode 검사
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text != '00':
            result_msg = root.find('.//resultMsg')
            msg_text = result_msg.text if result_msg is not None else "Unknown Error"
            print(f"  ⚠️ KSD 배당 API 에러 반환: CODE={result_code.text}, MSG={msg_text}")
            return []
            
        items = root.findall('.//item')
        if not items:
            print("  ℹ️ 배당 및 배당락 일정이 존재하지 않습니다.")
            return []
            
        for item in items:
            company_name = item.findtext('korSecnNm', default='').strip()
            # 배당락일 (dvdLkDt 또는 dvdExDt 등 공식 스펙 필드명 매칭)
            # KSD API의 배당락일 기본 필드명은 'dvdLkDt' 또는 'dvdExDt'
            # 배당지급일 기본 필드명은 'dvdPayDt' 또는 'payDt'
            dvd_ex_date_raw = item.findtext('dvdLkDt', default='').strip()
            dvd_pay_date_raw = item.findtext('dvdPayDt', default='').strip()
            dvd_amt_raw = item.findtext('dvdVal', default='0').strip()
            
            if not company_name:
                continue
                
            # 배당락 일정 등록
            if dvd_ex_date_raw and len(dvd_ex_date_raw) == 8:
                dvd_ex_date = f"{dvd_ex_date_raw[:4]}-{dvd_ex_date_raw[4:6]}-{dvd_ex_date_raw[6:]}"
                # 미래 일정 검증
                dvd_ex_dt = datetime.strptime(dvd_ex_date, '%Y-%m-%d')
                if dvd_ex_dt.date() >= today_dt.date():
                    schedules.append({
                        "date": dvd_ex_date,
                        "category": "배당/권리락",
                        "event": f"[배당락] {company_name} 배당락일",
                        "source": "예탁결제원"
                    })
                    
            # 배당금 지급일 등록
            if dvd_pay_date_raw and len(dvd_pay_date_raw) == 8:
                dvd_pay_date = f"{dvd_pay_date_raw[:4]}-{dvd_pay_date_raw[4:6]}-{dvd_pay_date_raw[6:]}"
                dvd_pay_dt = datetime.strptime(dvd_pay_date, '%Y-%m-%d')
                if dvd_pay_dt.date() >= today_dt.date():
                    try:
                        amt_float = float(dvd_amt_raw)
                        amt_str = f"{amt_float:,.0f}원" if amt_float.is_integer() else f"{amt_float:,}원"
                    except ValueError:
                        amt_str = f"{dvd_amt_raw}원"
                        
                    schedules.append({
                        "date": dvd_pay_date,
                        "category": "배당/권리락",
                        "event": f"[배당지급] {company_name} 주당 {amt_str} 배당금 지급일",
                        "source": "예탁결제원"
                    })
            
        print(f"  🎉 배당/배당락 일정 {len(schedules)}건 수집 완료!")
        return schedules
        
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ KSD 배당 API 통신 장애: {e}")
        return []
    except ET.ParseError:
        print("  ⚠️ XML 파싱 실패. 공공데이터포털 서버 일시 장애 또는 API 키 미승인 상태일 수 있습니다.")
        return []
    except Exception as ex:
        print(f"  ⚠️ 예상치 못한 오류: {ex}")
        return []

if __name__ == "__main__":
    res = get_ksd_dividends()
    for r in res:
        print(f"  - {r['date']} | {r['event']}")

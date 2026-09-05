import os
import requests
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 환경변수 또는 .env 파일에서 GEMINI_API_KEY 로드 (연구3 -> 연구2 순 탐색)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "adkan연구2" / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def generate_gemini_sector_analysis(sector_name: str, stocks: list, target_date: str = "2026-08-09") -> dict:
    """
    구글 Gemini 2.5 Flash API를 활용하여 5대 섹터의 강했던 이유 및 주요 일정을 고품질 정밀 생성
    """
    if not GEMINI_API_KEY:
        return None

    top_stocks = stocks[:10]
    stocks_str = ", ".join(top_stocks) if top_stocks else "대표 주도 종목"

    # target_date에서 연·월 동적 추출
    try:
        year_month = datetime.strptime(target_date, "%Y-%m-%d").strftime("%Y년 %m월")
    except Exception:
        year_month = target_date

    # 섹터 키워드 힌트 추출 (프롬프트 품질 향상)
    from sector_classifier import SECTOR_MAPPER
    sector_kw = SECTOR_MAPPER.get(sector_name, [])
    kw_hint = ", ".join([k for k in sector_kw if len(k) >= 3][:8])

    prompt = f"""당신은 대한민국 주식 시장 퀀트 섹터 전문 분석가입니다.
현재 시점 기준일자({target_date})에 맞춰 아래 주도 섹터와 포착된 대표 종목(최대 10개)을 바탕으로 '강했던 이유 및 핵심 업황(안착 이유)'과 '주요 일정(향후 모멘텀/공시/행사 등)'을 현실감 있게 작성해 주세요.

[입력 정보]
- 분석 기준일자: {target_date} (현재 기준)
- 섹터명: {sector_name}
- 섹터 핵심 키워드: {kw_hint}
- 대표 포착 종목 (최대 10개): {stocks_str}

[필수 작성 규칙 및 시점 제한 사항]
1. **시점 엄수**: 분석 기준일자({target_date})는 {year_month}입니다. 이미 지나간 과거 연도/분기를 절대 언급하지 마세요.
2. **실시간 모멘텀 반영**: 최근 시장 거래대금 쏠림, 3일선/5일선 이평선 안착 기술적 파동 및 해당 업황의 최신 글로벌/국내 트렌드를 기준으로 작성하세요.
3. **'강했던 이유'**: ①, ②, ③ 항목으로 3줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
4. **'주요 일정'**: 향후 예정된 섹터/기업의 주요 이벤트, 실적 발표, 학회/전시회, 수주 공시 등을 ①, ② 항목으로 2줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
5. '강했던 이유', '주요 일정' 같은 제목 문구를 절대 출력하지 마세요. 번호 항목만 출력하세요."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
    }

    try:
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            txt = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if txt and len(txt) > 30:
                lines = [l.strip() for l in txt.split("\n") if l.strip()]
                numbered = [l for l in lines if any(l.startswith(p) for p in ["①", "②", "③", "1.", "2.", "3."])]

                def strip_header(s):
                    s = re.sub(r'^[\*#\s]*(강했던 이유|핵심 업황|안착 이유|주요 일정)[^①-③0-9]*', '', s).strip()
                    s = re.sub(r'^[:\-\s]+', '', s).strip()
                    return s

                cleaned = [strip_header(l) for l in numbered]
                cleaned = [l for l in cleaned if l and len(l) > 5]

                schedule_kw = [l for l in cleaned if any(k in l for k in ["일정", "발표", "컨퍼런스", "공시", "모니터링", "로드맵", "전망"])]
                reason_kw = [l for l in cleaned if l not in schedule_kw]

                if not reason_kw and len(cleaned) >= 2:
                    reason_kw = cleaned[:3]
                    schedule_kw = cleaned[3:]

                if len(reason_kw) >= 2:
                    reason_formatted = "<br>".join(reason_kw[:3])
                    schedule_formatted = "<br>".join(schedule_kw[:2]) if schedule_kw else "① 주요 기업 분기 실적 발표 및 공시 일정<br>② 섹터 주요 기술 컨퍼런스 및 수주 일정"
                    logger.info(f"✨ [Gemini 2.5 Flash] '{sector_name}' 분석 연산 완료")
                    return {"reason": reason_formatted, "schedule": schedule_formatted, "used_llm": "gemini-2.5-flash"}
    except Exception as e:
        logger.warning(f"⚠️ Gemini API 연산 중 예외 발생: {e}")

    return None


def generate_llm_sector_analysis(sector_name: str, stocks: list, target_date: str = "2026-08-09", model_name: str = "gemma4:e4b") -> dict:
    """
    로컬 LLM (Ollama gemma4:e4b)을 호출하여 5대 섹터의 강했던 이유(안착 이유) 및 주요 일정을 생성
    """
    top_stocks = stocks[:10]
    stocks_str = ", ".join(top_stocks) if top_stocks else "대표 주도 종목"
    
    try:
        year_month = datetime.strptime(target_date, "%Y-%m-%d").strftime("%Y년 %m월")
    except Exception:
        year_month = target_date

    from sector_classifier import SECTOR_MAPPER
    sector_kw = SECTOR_MAPPER.get(sector_name, [])
    kw_hint = ", ".join([k for k in sector_kw if len(k) >= 3][:8])

    prompt = f"""당신은 대한민국 주식 시장 퀀트 섹터 전문 분석가입니다.
현재 시점 기준일자({target_date})에 맞춰 아래 주도 섹터와 포착된 대표 종목(최대 10개)을 바탕으로 '강했던 이유 및 핵심 업황(안착 이유)'과 '주요 일정'을 작성해 주세요.

[입력 정보]
- 분석 기준일자: {target_date} (현재 기준)
- 섹터명: {sector_name}
- 섹터 핵심 키워드: {kw_hint}
- 대표 포착 종목 (최대 10개): {stocks_str}

[출력 작성 수칙]
1. **시점 엄수**: 분석 기준일자({target_date})는 {year_month}입니다. 이미 지나간 과거 연도/분기를 언급하지 마세요.
2. '강했던 이유': ①, ②, ③ 항목으로 3줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
3. '주요 일정': ①, ② 항목으로 2줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
4. '강했던 이유', '주요 일정' 같은 제목 문구를 절대 출력하지 마세요. 번호 항목만 출력하세요."""

    url = "http://localhost:11434/api/generate"
    for m in [model_name, "exaone3.5:7.8b", "qwen2.5:7b", "gemma4:e2b"]:
        try:
            payload = {"model": m, "prompt": prompt, "stream": False}
            res = requests.post(url, json=payload, timeout=45)
            if res.status_code == 200:
                txt = res.json().get("response", "").strip()
                if txt and len(txt) > 50:
                    # 간단 파싱 (이유와 일정 분리) — 헤더/제목 라인 제거
                    lines = [line.strip() for line in txt.split("\n") if line.strip()]
                    # 번호(①②③ 또는 1.2.3.)로 시작하는 실질 항목만 추출
                    numbered = [l for l in lines if any(l.startswith(p) for p in ["①", "②", "③", "1.", "2.", "3."])]
                    # 헤더 문구 제거 후처리
                    def strip_header(s):
                        import re
                        s = re.sub(r'^[\*#\s]*(강했던 이유|핵심 업황|안착 이유|주요 일정)[^①-③0-9]*', '', s).strip()
                        s = re.sub(r'^[:\-\s]+', '', s).strip()
                        return s
                    cleaned = [strip_header(l) for l in numbered]
                    cleaned = [l for l in cleaned if l and len(l) > 5]
                    
                    # 일정 항목 분리 ("일정"/"발표"/"컨퍼런스" 키워드)
                    schedule_kw = [l for l in cleaned if any(k in l for k in ["일정", "발표", "컨퍼런스", "공시", "모니터링", "로드맵"])]
                    reason_kw = [l for l in cleaned if l not in schedule_kw]
                    
                    if len(reason_kw) >= 2:
                        reason_formatted = "<br>".join(reason_kw[:3])
                        schedule_formatted = "<br>".join(schedule_kw[:2]) if schedule_kw else "① 주요 기업 분기 실적 발표 및 공시 일정<br>② 섹터 주요 기술 컨퍼런스 및 수주 일정"
                        return {"reason": reason_formatted, "schedule": schedule_formatted, "used_llm": m}
        except Exception:
            continue
            
    return None


def get_dynamic_sector_info(sector_name: str, stocks: list, target_date: str = "2026-07-31") -> dict:
    """
    1. 구글 Gemini 2.5 Flash API 우선 호출 (고품질 정밀 퀀트 요약)
    2. 네트워크 장애/키 미설정 시 로컬 LLM (gemma4:e4b) 폴백
    3. 로컬 LLM 타임아웃 시 룰기반 템플릿 최종 폴백
    """
    # 1차: 구글 Gemini 2.5 Flash API
    gemini_res = generate_gemini_sector_analysis(sector_name, stocks, target_date=target_date)
    if gemini_res:
        return gemini_res

    # 2차: 로컬 Ollama LLM (gemma4:e4b)
    llm_res = generate_llm_sector_analysis(sector_name, stocks, target_date=target_date, model_name="gemma4:e4b")
    if llm_res:
        return llm_res

    parser = NewsMomentumParser()
    bulletins = parser.parse_premarket_news(target_date)
    
    top_stocks = stocks[:10]
    target_stocks_str = ", ".join(top_stocks[:3]) if top_stocks else "대표 주도주"
    
    if "반도체" in sector_name or "AI" in sector_name:
        reason = (
            f"① 반도체/AI 소부장 수급 쏠림: {target_stocks_str} 등 AI 서버 및 차세대 메모리 모멘텀 보유 종목군으로 동시 수급 유입<br>"
            f"② 실적 턴어라운드 기대감: 주요 소부장 강소기업들의 실적 개선세 가시화 및 고성능 칩 기술력 재부각<br>"
            f"③ 기술적 이평선 수렴 지지: 장기 조정 후 거래량을 동반한 이평선 안착 및 반등 파동 형성"
        )
        schedule = (
            f"① 글로벌 빅테크 및 반도체 주요 기업 분기 실적 발표 일정<br>"
            f"② 차세대 AI 칩 및 온디바이스 AI 탑재 신제품 론칭 일정"
        )
    elif "바이오" in sector_name or "제약" in sector_name or "헬스케어" in sector_name:
        reason = (
            f"① 바이오/헬스케어 바닥권 반등: {target_stocks_str} 등 임상 파이프라인 및 의료기기 강소기업 중심 대량 거래량 유입<br>"
            f"② 글로벌 학회 및 임상 모멘텀: 주요 바이오 학회 수혜 기대감과 글로벌 제약사 기술이전 기대감 동반 부각<br>"
            f"③ 글로벌 규제 반사이익: 생물보안 이슈 등 글로벌 밸류체인 재편에 따른 국내 CMO/CDMO 수혜 감지"
        )
        schedule = (
            f"① 다가오는 글로벌 임상 학회 발표 및 해외 바이오 컨퍼런스 일정<br>"
            f"② 주요 임상 파이프라인 데이터 공개 및 FDA/EMA 승인 관련 일정"
        )
    elif "밸류업" in sector_name or "지주" in sector_name or "저PBR" in sector_name:
        reason = (
            f"① 주주환원 및 밸류업 모멘텀: {target_stocks_str} 등 PBR 1배 미만 소외 지주사 및 자사주 소각/배당 확대 기업 주가 정상화<br>"
            f"② 경영 효율성 및 지배구조 개편: 기업 가치 제고 계획 자율공시 확대 및 지주사 순자산가치(NAV) 재평가<br>"
            f"③ 기관/외국인 수급 유입: 안전자산 매력과 고배당 수익률 바탕 코스피 시장 대비 우상향 추세 지지"
        )
        schedule = (
            f"① 한국거래소 밸류업 가이드라인 이행 현황 및 자율공시 일정<br>"
            f"② 주요 지주사 및 금융사 분기 자사주 소각/배당 공시 일정"
        )
    elif "로봇" in sector_name or "스마트팩토리" in sector_name or "자동화" in sector_name:
        reason = (
            f"① 지능형 로봇 및 자동화 확산: {target_stocks_str} 등 스마트팩토리 제어 부품 및 협동로봇 밸류체인 순환매 가속화<br>"
            f"② 오버행 우려 해소 및 수급 정상화: 잠재적 매도 물량 흡수 후 기관·외국인 메이저 수급 강하게 유입<br>"
            f"③ 대기업 제조 공장 내 도입 기대: AI 융합 로봇 솔루션의 산업 현장 즉시 투입 및 부품 공급망 확대"
        )
        schedule = (
            f"① 글로벌 로봇 테크 콘퍼런스 및 산업 자동화 박람회 일정<br>"
            f"② 주요 제조 기업 협동/자율이동로봇(AMR) 신규 채택 발표 일정"
        )
    elif "방산" in sector_name or "항공우주" in sector_name:
        reason = (
            f"① 글로벌 지정학적 리스크 확대: {target_stocks_str} 등 국내 방산 수출 계약 급증 및 방위비 증액 수혜 기대감으로 외국인 수급 집중<br>"
            f"② K-방산 수출 확대: 폴란드·중동·동남아 등 신규 수출국 계약 추진 가시화로 밸류에이션 리레이팅<br>"
            f"③ 국내 군비 현대화: 국방예산 증액 기조에 따른 국내 수주 파이프라인 확대 및 실적 가시성 향상"
        )
        schedule = (
            f"① 국내외 방산 수출 계약 공시 및 수주 잔고 발표 일정<br>"
            f"② 글로벌 방위산업 전시회(DSEI, MSPO 등) 및 방위사업청 발표 일정"
        )
    elif "조선" in sector_name or "해양" in sector_name:
        reason = (
            f"① 글로벌 LNG 운반선·컨테이너선 발주 급증: {target_stocks_str} 등 수주잔고 사상 최고치 경신으로 실적 가시성 극대화<br>"
            f"② 고부가 선박 수익성 개선: LNG선·LCO2 선박 등 고마진 선종 비중 확대에 따른 영업이익률 상승<br>"
            f"③ 기자재 공급망 국산화: 선박 엔진·의장품 국산화율 상승으로 국내 기자재 업체 동반 수혜 수급 유입"
        )
        schedule = (
            f"① 주요 조선사 신규 수주 공시 및 분기 수주잔고 업데이트 일정<br>"
            f"② 글로벌 조선·해양 전시회(Gastech, Posidonia 등) 및 해수부 정책 발표 일정"
        )
    elif "원자력" in sector_name or "원전" in sector_name:
        reason = (
            f"① 글로벌 원전 르네상스: {target_stocks_str} 등 탄소중립 기조 속 원전 재평가 및 SMR 상용화 기대감으로 섹터 전반 부각<br>"
            f"② 해외 수출 모멘텀: 체코·폴란드·사우디 등 APR1400 수출 계약 추진으로 수주 기대감 지속<br>"
            f"③ 국내 원전 유지·보수 수요: 설계 수명 연장 및 신규 원전 가동 준비에 따른 정비·서비스 수요 급증"
        )
        schedule = (
            f"① 해외 원전 수출 입찰 결과 및 계약 체결 공시 일정<br>"
            f"② 원자력진흥위원회 정책 발표 및 에너지 기본계획 관련 일정"
        )
    elif "2차전지" in sector_name or "배터리" in sector_name:
        reason = (
            f"① 전기차 보급 가속화: {target_stocks_str} 등 글로벌 완성차 OEM의 배터리 장기 공급 계약 체결로 실적 가시성 향상<br>"
            f"② 소재 밸류체인 수혜: 양극재·음극재·전해질 등 핵심 소재 국산화 가속 및 단가 인하 수혜 기대<br>"
            f"③ ESS 수요 급증: 재생에너지 보급 확대에 따른 대규모 에너지저장장치 프로젝트 수주 확대"
        )
        schedule = (
            f"① 주요 배터리 셀·소재 기업 수주 및 JV 계약 공시 일정<br>"
            f"② 글로벌 EV 전시회(CES, 모터쇼 등) 및 배터리 업계 컨퍼런스 일정"
        )
    elif "신재생" in sector_name or "태양광" in sector_name or "풍력" in sector_name:
        reason = (
            f"① 글로벌 에너지 전환 가속: {target_stocks_str} 등 정부 해상풍력·태양광 발전 목표 상향으로 수주 기회 급증<br>"
            f"② 전력망 안정화 수요: 재생에너지 발전 확대에 따른 변압기·차단기·ESS 관련 인프라 투자 활발<br>"
            f"③ 미국 IRA 및 유럽 REPowerEU 수혜: 해외 프로젝트 수주 가시화로 성장 스토리 재부각"
        )
        schedule = (
            f"① 정부 재생에너지 발전 허가 및 입찰 결과 발표 일정<br>"
            f"② 글로벌 에너지 전시회(WindEurope, Intersolar 등) 및 국내 그린에너지 정책 일정"
        )
    elif "자동차" in sector_name or "전장" in sector_name:
        reason = (
            f"① 전기차 전환 수혜: {target_stocks_str} 등 전장부품 국산화 수혜 및 ADAS 탑재 확대로 ASP 상승 기대<br>"
            f"② 하이브리드 전환기 수혜: 전기차 캐즘 국면에서 하이브리드 수요 급증에 따른 부품 공급 확대<br>"
            f"③ 수출 다변화: 미국·유럽·인도 시장 현지화 전략 가속으로 글로벌 OEM 납품 확대"
        )
        schedule = (
            f"① 완성차 및 부품사 분기 실적 발표 및 수주 공시 일정<br>"
            f"② 글로벌 모터쇼 및 CES 전장·자율주행 관련 발표 일정"
        )
    elif "철강" in sector_name or "금속" in sector_name:
        reason = (
            f"① 조선·건설 수요 연계 강세: {target_stocks_str} 등 후판·형강 수요 확대에 따른 판가 상승 기대감으로 수급 유입<br>"
            f"② 원자재 가격 안정화: 철광석·코크스 원가 부담 완화로 마진 개선 기대<br>"
            f"③ 전기로 전환 및 탄소 감축 투자: 친환경 철강 전환 투자 기대감으로 밸류에이션 재평가"
        )
        schedule = (
            f"① 철강 업체 분기 실적 및 판가 인상 공시 일정<br>"
            f"② 글로벌 원자재 가격(LME, SHFE) 주요 발표 일정"
        )
    elif "건설" in sector_name or "인프라" in sector_name:
        reason = (
            f"① 해외 플랜트 및 인프라 수주 확대: {target_stocks_str} 등 중동·동남아 대규모 프로젝트 수주로 수주잔고 급증<br>"
            f"② 국내 재건축·재개발 규제 완화: 도심 정비사업 수혜 기대감 부각<br>"
            f"③ 공공 SOC 투자 확대: 정부 인프라 예산 증액 기조에 따른 관급 공사 수주 기회 확대"
        )
        schedule = (
            f"① 주요 해외 건설 수주 공시 및 입찰 결과 발표 일정<br>"
            f"② 국내 정비사업 관련 정책 발표 및 주요 단지 착공·분양 일정"
        )
    elif "해운" in sector_name or "물류" in sector_name:
        reason = (
            f"① 해운 운임 반등: {target_stocks_str} 등 컨테이너·벌크 운임 상승 사이클 재진입으로 실적 개선 기대<br>"
            f"② 지정학적 리스크 수혜: 홍해 우회 항로 운임 강세 지속으로 수익성 향상<br>"
            f"③ 화물 물동량 회복: 글로벌 교역 회복에 따른 물동량 증가로 가동률 상승"
        )
        schedule = (
            f"① 글로벌 해운 운임 지수(BDI, SCFI) 주요 발표 일정<br>"
            f"② 주요 해운·물류 기업 분기 실적 발표 일정"
        )
    elif "K-뷰티" in sector_name or "화장품" in sector_name:
        reason = (
            f"① K-뷰티 글로벌 확산: {target_stocks_str} 등 미국·일본·동남아 ODM 수출 급증으로 매출 고성장<br>"
            f"② 인디 브랜드 경쟁력 부각: 중소형 K뷰티 브랜드의 아마존·틱톡 채널 성과 가시화로 밸류에이션 재평가<br>"
            f"③ 중국 시장 회복 기대: 중국 소비 심리 회복 기조에 따른 면세·현지 채널 매출 반등 기대"
        )
        schedule = (
            f"① 국내외 뷰티·코스메틱 박람회(CosmoProf, K-Beauty Expo 등) 일정<br>"
            f"② 주요 ODM·OEM 업체 분기 수주 실적 공시 일정"
        )
    elif "K-콘텐츠" in sector_name or "게임" in sector_name or "엔터" in sector_name:
        reason = (
            f"① K-콘텐츠 글로벌 흥행: {target_stocks_str} 등 넷플릭스·디즈니+ IP 흥행 성과로 밸류에이션 리레이팅<br>"
            f"② 게임 신작 출시 효과: 기대작 글로벌 출시 전후 이용자 급증 및 인앱 수익 가시화<br>"
            f"③ K팝 아티스트 컴백 및 월드투어: 공연·MD·음원 수익 집중으로 실적 모멘텀 부각"
        )
        schedule = (
            f"① 주요 게임 신작 글로벌 출시 일정 및 오픈베타 일정<br>"
            f"② K팝 아티스트 컴백 및 글로벌 공연 일정"
        )
    elif "핀테크" in sector_name or "가상자산" in sector_name or "금융" in sector_name:
        reason = (
            f"① 금리 인하 기대감 부각: {target_stocks_str} 등 금융주 NIM 안정화 및 대출 성장 기대로 외국인 수급 유입<br>"
            f"② 가상자산 시장 규제 명확화: 제도권 편입 기대감으로 핀테크·거래소 관련주 급등<br>"
            f"③ 밸류업 프로그램 연계: 고배당·자사주 소각 기대 금융주 저PBR 해소 흐름"
        )
        schedule = (
            f"① 한국은행 기준금리 결정 발표 및 금융통화위원회 일정<br>"
            f"② 금융위원회 가상자산·핀테크 규제 관련 정책 발표 일정"
        )
    elif "전력기기" in sector_name or "전선" in sector_name or "변압기" in sector_name:
        reason = (
            f"① AI 데이터센터 전력 수요 급증: {target_stocks_str} 등 변압기·전선 수주 잔고 급증으로 실적 가시성 최고조<br>"
            f"② 글로벌 전력망 현대화: 미국·유럽 노후 송전망 교체 투자 확대로 국내 전력기기 수출 급증<br>"
            f"③ 신재생에너지 연계 인프라: 해상풍력·태양광 연계 해저케이블·변압기 수요 폭발적 증가"
        )
        schedule = (
            f"① 주요 전력기기·전선 업체 해외 수주 공시 일정<br>"
            f"② 글로벌 전력 인프라 투자 계획(IRA, REPowerEU) 관련 정부 발표 일정"
        )
    elif "통신" in sector_name or "5G" in sector_name:
        reason = (
            f"① 5G·6G 인프라 투자 확대: {target_stocks_str} 등 국내외 통신사 기지국 장비 발주 재개로 수혜 부각<br>"
            f"② AI 기반 네트워크 최적화: AI-RAN 및 Open RAN 기술 적용 확대로 국내 장비 업체 점유율 확대<br>"
            f"③ 통신사 고배당·밸류업: 안정적 현금창출력 바탕 고배당 지속 기대로 외국인 매수 유입"
        )
        schedule = (
            f"① 5G 주파수 할당 및 통신 장비 발주 공시 일정<br>"
            f"② 글로벌 통신 전시회(MWC) 및 주요 통신사 분기 실적 발표 일정"
        )
    elif "화학" in sector_name or "정밀화학" in sector_name:
        reason = (
            f"① 원자재 가격 안정화: {target_stocks_str} 등 납사·원유 가격 하향 안정으로 스프레드 개선 기대<br>"
            f"② 반도체·배터리 소재 수혜: 특수가스·전자재료 수요 증가로 정밀화학 업체 실적 개선<br>"
            f"③ 친환경 화학 전환: 바이오플라스틱·재활용 소재 사업 확장으로 장기 성장 스토리 부각"
        )
        schedule = (
            f"① 주요 화학업체 분기 실적 및 증설 투자 계획 공시 일정<br>"
            f"② 글로벌 석유화학 원자재(납사, WTI) 가격 발표 일정"
        )
    else:
        reason = (
            f"① 주도 섹터 기술적 순환매: {target_stocks_str} 중심의 거래량 급증 및 기술적 이평선 수렴 안착<br>"
            f"② 업종 실적 개선 모멘텀: 수급 유입과 함께 주가 저점 탈피 추세 전환 형성<br>"
            f"③ 차트 3일선/5일선 지지 파동: 눌림목 구간 정밀 지지 확인"
        )
        schedule = (
            f"① 주요 기업 분기 실적 발표 및 경영 성과 공유회 일정<br>"
            f"② 업종별 주요 파트너십 및 수주 공시 일정"
        )

    return {"reason": reason, "schedule": schedule}


def generate_single_markdown_table(top5_sectors: list, table_title: str, target_date: str = "2026-07-31") -> str:
    """
    엑셀 바로 붙여넣기 100% 호환 단일 마크다운 표 (Single Markdown Table) 동적 생성 (종목명 최대 10개 제한)
    """
    md = f"### 📊 {table_title}\n\n"
    md += "| 섹터명 | 강했던 이유 및 핵심 업황 | 주요 일정 | 종목 |\n"
    md += "| :--- | :--- | :--- | :--- |\n"

    for sec in top5_sectors:
        sec_name = sec["sector_name"]
        stocks_list = sec["stocks"][:10]  # 유저 요구사항: 섹터당 종목명 최대 10개 제한
        stocks_str = ", ".join(stocks_list) if stocks_list else "대표 주도 종목 전수 스캔"
        
        info = get_dynamic_sector_info(sec_name, sec["stocks"], target_date=target_date)

        reason_str = info["reason"]
        schedule_str = info["schedule"]

        md += f"| **{sec_name}** | {reason_str} | {schedule_str} | {stocks_str} |\n"

    md += "\n---\n\n"
    return md

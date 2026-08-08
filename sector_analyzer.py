import os
import requests
import json
import logging
import re
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 환경변수 또는 .env 파일에서 GEMINI_API_KEY 로드 (연구3 -> 연구2 순 탐색)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "adkan연구2" / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def generate_gemini_sector_analysis(sector_name: str, stocks: list) -> dict:
    """
    구글 Gemini 2.5 Flash API를 활용하여 5대 섹터의 강했던 이유 및 주요 일정을 고품질 정밀 생성
    """
    if not GEMINI_API_KEY:
        return None

    top_stocks = stocks[:10]
    stocks_str = ", ".join(top_stocks) if top_stocks else "대표 주도 종목"

    prompt = f"""당신은 대한민국 주식 시장 퀀트 섹터 전문 분석가입니다.
아래 주도 섹터와 포착된 대표 종목(최대 10개)을 바탕으로 '강했던 이유 및 핵심 업황(안착 이유)'과 '주요 일정'을 작성해 주세요.

[입력 정보]
- 섹터명: {sector_name}
- 대표 포착 종목 (최대 10개): {stocks_str}

[출력 작성 수칙]
1. '강했던 이유': ①, ②, ③ 항목으로 3줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
2. '주요 일정': ①, ② 항목으로 2줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
3. '강했던 이유', '주요 일정' 같은 제목 문구를 절대 출력하지 마세요. 번호 항목만 출력하세요."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
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


def generate_llm_sector_analysis(sector_name: str, stocks: list, model_name: str = "gemma4:e4b") -> dict:
    """
    로컬 LLM (Ollama gemma4:e4b)을 호출하여 5대 섹터의 강했던 이유(안착 이유) 및 주요 일정을 생성
    """
    top_stocks = stocks[:10]
    stocks_str = ", ".join(top_stocks) if top_stocks else "대표 주도 종목"
    
    prompt = f"""당신은 대한민국 주식 시장 퀀트 섹터 전문 분석가입니다.
아래 주도 섹터와 포착된 대표 종목(최대 10개)을 바탕으로 '강했던 이유 및 핵심 업황(안착 이유)'과 '주요 일정'을 작성해 주세요.

[입력 정보]
- 섹터명: {sector_name}
- 대표 포착 종목 (최대 10개): {stocks_str}

[출력 작성 수칙]
1. '강했던 이유': ①, ②, ③ 항목으로 3줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
2. '주요 일정': ①, ② 항목으로 2줄 요약 (각 항목 뒤에 <br> 추가). 제목/헤더 없이 ① 부터 바로 시작.
3. '강했던 이유', '주요 일정' 같은 제목 문구를 절대 출력하지 마세요. 번호 항목만 출력하세요."""

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
    gemini_res = generate_gemini_sector_analysis(sector_name, stocks)
    if gemini_res:
        return gemini_res

    # 2차: 로컬 Ollama LLM (gemma4:e4b)
    llm_res = generate_llm_sector_analysis(sector_name, stocks, model_name="gemma4:e4b")
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

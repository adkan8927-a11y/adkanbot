# 🤖 연구3 스크리닝 & 배포 에이전트 가이드 (AGENTS_연구3.md)

> [!IMPORTANT]
> 본 프로젝트의 전체 기술 스택, 시스템 아키텍처, 3대 매매 전략 명세 및 파이프라인 흐름은 **반드시 [`ARCHITECTURE_연구3.md`](file:///Users/adkan/adkan연구3/ARCHITECTURE_연구3.md) (또는 [`docs/architecture.md`](file:///Users/adkan/adkan연구3/docs/architecture.md))를 참고**해 주시기 바랍니다.

이 문서는 `adkan연구3` 프로젝트를 구성하는 핵심 자동화 모듈, 데이터 수집 에이전트, 스크리너 엔진, 차트 생성기, 텔레그램 배포 봇의 역할과 사용법을 정의합니다.

---

## 🤖 핵심 모듈 및 에이전트 역할

### 1. 오케스트레이터 & 마스터 파이프라인
- **`run_screening_pipeline.py` (★ 마스터 배포 파이프라인)**:
  - 전체 수집, 스크리닝, 차트 작성, 텔레그램 TOP3 발송, Git Push를 원스톱으로 관리하는 통합 컨트롤러입니다.
  - 실행 시 500개 종목 스캔 ➔ 전략 간 중복 제거(`seen_codes`) ➔ 고해상도 이평선 차트 PNG 생성 ➔ MD & HTML 종합 보고서 빌드 ➔ 텔레그램 TOP3 메시지/차트 발송 ➔ `adkanbot` GitHub 저장소 자동 `git commit & push`를 완수합니다.
- **`main.py` (CLI 통합 실행기)**:
  - 3대 핵심 전략(전략1, 전략2, 전략3)을 명령줄 옵션(`--strategy 1|2|3`)에 따라 개별 또는 순차 스캔할 수 있는 프론트엔드 모듈입니다.

### 2. 시세 및 수급 수집 에이전트
- **`collector.py` (데이터 수집 엔진)**:
  - `FinanceDataReader` (FDR) 및 `pykrx` 라이브러리를 활용해 KRX 거래대금 상위 500개 종목 리스트와 최근 320일간의 일봉 OHLCV 데이터를 수집합니다.
- **`kis_client.py` (한국투자증권 OpenAPI 통신 에이전트)**:
  - KIS Developers OAuth2 Access Token을 발급받아 캐싱(`.token_cache.json`) 관리합니다.
  - 모의투자/실전투자 API 서버(`openapivts.koreainvestment.com:29443`)를 통해 종목별 현재가 및 최근 20일간 외국인/기관 누적 수급 데이터를 실시간 수집합니다.

### 3. 조건검색 및 전략 평가 엔진
- **`screener.py` (3대 핵심 전략 스크리너)**:
  - **`screen_strategy1_yang_eum_yang()`**: 장대양봉/상한가 기준봉 형성 후 3/5/8/13/20일 이동평균선 상에서 거래량이 급감한 양-음-양 눌림목 및 '사윗감' 패턴을 포착합니다.
  - **`screen_strategy2_iilhong()`**: 과거 200억 이상 거래대금 급증 매집봉 발생 후 1개월 조정을 거쳐 240일 장기 추세선(-0.20%)에 정밀 접지한 이일홍 정석 패턴을 탐색합니다.
  - **`screen_strategy3_sugeub_halt()`**: 52주 고점 대비 40% 이상 폭락(<= 66%)한 낙폭과대 구간에서 최근 20일 기관/외국인 메이저 수급이 유입되며 바닥 이평선을 핥는 수급 바닥형 패턴을 검증합니다.

### 4. 시각화 및 배포 에이전트
- **`chart_drawer.py` (맞춤 이평선 차트 캡처 에이전트)**:
  - `mplfinance` 기반 한국 주식 전용 양봉(빨강)/음봉(파랑) 스타일 일봉 차트를 생성합니다.
  - 전략별 맞춤 이동평균선(전략1: 3/5/8/13/20일, 전략2: 20/120/240일, 전략3: 20/60/120/240일)을 명확하게 도출하며 대형 가독성 폰트로 `charts/` 디렉토리에 PNG 파일로 저장합니다.
- **`telegram_bot.py` (텔레그램 자동 배포 봇)**:
  - Telegram Bot API를 통해 전략별 TOP 선택 종목의 핵심 가격 전략(매수가/목표가/손절가) 텍스트 메시지 및 차트 이미지(`send_photo`)를 전송합니다.

### 5. 테스트 & 백테스트 모듈 (`tests/`, `backtests/`)
- **`backtests/simulate_live_trading.py`**: 실전플랜1 기준 20거래일 시뮬레이션 및 전략별 승률/손익을 계산합니다.
- **`backtests/analyze_monthly_performance.py`**: 월간 매매 성과 추적 스크립트.
- **`tests/test_telegram.py` & `tests/test_investor.py`**: 텔레그램 연동 및 수급 API 모듈의 개별 단위 테스트.

---

## 🔒 운영 수칙 및 개발 가이드라인

1. **보안 관리**: KIS API AppKey, Secret 및 Telegram Token은 최상위 `.env`에 보관하며 절대로 Git에 하드코딩하여 커밋하지 않습니다.
2. **종목 전략 중복 방지**: 한 종목이 복수 전략 조건에 충족할 경우 우선순위(전략 1 ➔ 전략 2 ➔ 전략 3)에 따라 최초 선택된 전략에만 단독 배치합니다.
3. **독립 실행 테스트**: 모든 단위 모듈은 독립적으로 실행(`python3 kis_client.py` 또는 `python3 chart_drawer.py`)하여 검증할 수 있습니다.

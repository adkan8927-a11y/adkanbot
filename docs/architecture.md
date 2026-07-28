# System Architecture

본 문서는 프로젝트의 전체 기술 스택, 폴더 구조, 핵심 모듈의 역할 및 데이터 흐름을 정의합니다. 
앞으로 중요한 구조 변경이 생길 경우, **반드시 본 문서(`architecture.md`)를 함께 최신화**해야 합니다.

## 1. 기술 스택 (Tech Stack)
- **언어 및 프레임워크**: Python 3.9+
- **보안 및 환경 변수**: `python-dotenv` (`.env` 파일 기반 API 키 및 보안 자격증명 관리)
- **주요 라이브러리**: 
  - `pandas` (데이터베이스 CSV 조작 및 전처리)
  - `BeautifulSoup`, `requests`, `selenium` (웹 크롤링 및 API 통신)
  - `pdfplumber` (PDF 정적 데이터 파싱)
  - `sentence-transformers` (VIP 모멘텀 임베딩 기반 의미적 중복 제거)
- **프론트엔드**: Vanilla HTML, CSS, JavaScript (정적 웹호스팅 최적화)
- **자동화 인프라**: GitHub Actions, Mac `launchd`, `cron-job.org`

## 2. 폴더 구조 (Directory Structure)
```
/ (Project Root)
├── .env                         # 🔒 API 키 및 자격증명 (Git 추적 제외)
├── docs/                        # 시스템 아키텍처 등 주요 문서
│   └── architecture.md          # 👈 현재 문서
├── AGENTS.md                    # 전체 에이전트 목록 및 역할 (참조 필수)
├── index.html                   # 🎯 메인 대시보드 (뉴스 리포트 + 주간 캘린더 + 베타테스트 패널)
├── generate_index.py            # 메인 대시보드(index.html) 생성기
├── reports/                     # 에이전트가 요약한 데일리 뉴스 리포트 HTML (장전/장중/장후/주말)
├── 데일리뉴스*.py                # 뉴스 크롤러 봇 스크립트들 (.env 기반 보안 구동)
└── schedule check/              # 글로벌 투자 일정 및 VIP 모멘텀 스케줄러 시스템
    ├── master_schedule_db.csv   # 전체 일정이 누적되는 마스터 데이터베이스
    ├── vip_momentum_alerts.csv  # VIP 돌발 핫 모멘텀 데이터베이스
    ├── schedule.html            # 🎯 투자 일정 전용 대시보드
    ├── schedule_orchestrator.py # 모든 일정 에이전트를 조율하는 중앙 컨트롤러
    └── agents/                  # 데이터 소스별 개별 크롤러/파서 (DART, FRED, KSD 등)
```

## 3. 주요 모듈 역할 (Key Modules)
- **`schedule_orchestrator.py`**:
  - `agents/` 내부에 있는 모든 단위 에이전트를 순차적으로 호출하여 일정을 수집합니다.
  - 수집된 일정을 병합하고, 과거 데이터를 지우며, `SentenceTransformer`를 활용해 중복된 VIP 모멘텀 이슈를 필터링합니다.
  - 대시보드 렌더링 시 **권리락(`[종목명] 유상/무상증자 권리락`) 및 보호예수(`[종목명] 의무보유 해제`) 텍스트를 깔끔하게 자동 정제**합니다.
  - 베타테스트 패널 및 6분할 그리드가 적용된 투자 일정 대시보드 `schedule.html`을 렌더링하고 배포합니다.
- **`generate_index.py`**:
  - 데일리 뉴스 파이프라인에서 생성된 `reports/` 리포트들과 `master_schedule_db.csv`의 단기 일정을 읽어옵니다.
  - 동일한 이벤트 텍스트 정제 룰을 적용하여 메인 포털 화면인 `index.html`을 생성합니다.
- **`agents/*`**:
  - 각각의 외부 소스(DART 공시, FRED 매크로 API, 정부 부처 RSS, 예탁결제원 PDF 등)에 맞게 특화된 파싱 로직을 담당합니다. 자세한 목록은 `AGENTS.md`를 참고하세요.

## 4. 데이터 흐름 및 NLP 정제 알고리즘 (Data Flow & NLP Processing)
1. **[Trigger]**: 크론잡(Cron-job.org / Launchd)이 지정된 시간(예: 05:30, 11:30, 17:30, 23:30)에 백그라운드에서 스크립트를 실행합니다.
2. **[Security Authentication]**: `python-dotenv`가 `.env`에서 보안키를 로드하여 안전하게 외부 API(DART, Gemini, Telegram 등)와 통신합니다.
3. **[Scraping & Title-Only Embedding Routing]**:
   - `데일리뉴스(장전).py` 및 `데일리뉴스(장후).py`가 키워드 DB (`키워드3.json` / `키워드4.json`) 기반으로 네이버 뉴스 API 및 글로벌 RSS를 파싱합니다.
   - **기사 본문(Description) 낚시 단어로 인한 오탐 라우팅을 100% 차단**하기 위해 1차/2차 수집 및 임베딩 유사도 라우팅을 **제목 전용(`Title-Only`)으로만 수행**합니다. (Title-Only 골디락스 임계치 `0.50` 적용)
4. **[Financial Amount Priority Deduplication]**:
   - 동일 섹터 또는 전역 중복 검사(유사도 70% 이상) 시, 새로 검사되는 기사 제목에 **`29조원`, `1367억`, `198억달러` 등 구체적인 수주/투자 금액 수치가 명시되어 있고 기존 기사에는 없는 경우, 금액 명시 고가치 기사로 자동 교체**합니다.
5. **[Storage & Rendering]**:
   - 원본 일정 데이터는 `master_schedule_db.csv` 와 `vip_momentum_alerts.csv` 에 유지합니다.
   - 렌더링 직전 `[권리락] [종목명] ...` 형태를 `[종목명] 유상/무상증자 권리락` 형태로 일관되게 정제합니다.
   - `generate_index.py`를 호출하여 `schedule.html` 및 메인 포털 화면 `index.html`을 각각 렌더링합니다.
6. **[Deploy]**: 변경된 파일(CSV, HTML, MD)을 `git commit & push` 하여 GitHub Pages 라이브 서버에 실시간 배포합니다.

## 5. 🔑 GitHub Secrets & API 키 동기화 체크리스트 (GitHub Secrets Checklist)

깃허브 액션(GitHub Actions) 자동 실행 시 `Process completed with exit code 1` 등의 오류를 방지하기 위해 **GitHub Repository Secrets**가 최신 상태로 관리되어야 합니다.

### 필수 등록 Secrets 목록 (`Settings -> Secrets and variables -> Actions`)
| Secret 이름 | 용도 및 설명 | 필수 여부 |
| :--- | :--- | :---: |
| `GEMINI_API_KEY` | 구글 Gemini AI 리포트 섹터별 3줄 요약 및 영문 기사 한국어 번역 | **필수** |
| `NAVER_CLIENT_ID` | 네이버 뉴스 검색 API 클라이언트 ID | **필수** |
| `NAVER_CLIENT_SECRET` | 네이버 뉴스 검색 API 클라이언트 Secret | **필수** |
| `DART_API_KEY` | 금융감독원 DART 전자공시 OpenAPI 인증키 | **필수** |
| `TELEGRAM_BOT_TOKEN` | 리포트 생성 완료 텔레그램 알림 봇 토큰 | 선택 |
| `TELEGRAM_CHAT_ID` | 텔레그램 알림 수신 채널 / 채팅방 ID | 선택 |

### 🚨 트러블슈팅 및 장애 예방 규칙
1. **API 키 재발급 시 동기화 의무**: API 키(Gemini, Naver, Telegram 등)나 깃허브 PAT 토큰을 새로 발급받았을 경우, **로컬 `.env` 파일과 GitHub Secrets 양쪽 모두에 즉시 동기화 반영**해야 합니다. (Secrets 미업데이트 시 API 예외로 깃허브 액션 종료됨)
2. **Node.js Deprecation 경고 해석**: 깃허브 액션 로그의 `Node.js 20 is deprecated...` 문구는 Runner 런타임 버전 변경 안내 경고(Warning)이며, 빌드 실패(Exit Code 1)의 직접 원인이 아닙니다. Exit Code 1 발생 시 Secrets 키의 유효성을 최우선 점검해야 합니다.


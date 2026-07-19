# System Architecture

본 문서는 프로젝트의 전체 기술 스택, 폴더 구조, 핵심 모듈의 역할 및 데이터 흐름을 정의합니다. 
앞으로 중요한 구조 변경이 생길 경우, **반드시 본 문서(`architecture.md`)를 함께 최신화**해야 합니다.

## 1. 기술 스택 (Tech Stack)
- **언어 및 프레임워크**: Python 3.9+
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
├── docs/                        # 시스템 아키텍처 등 주요 문서
│   └── architecture.md          # 👈 현재 문서
├── AGENTS.md                    # 전체 에이전트 목록 및 역할 (참조 필수)
├── index.html                   # 🎯 메인 대시보드 (뉴스 리포트 + 주간 캘린더)
├── generate_index.py            # 메인 대시보드(index.html) 생성기
├── reports/                     # 에이전트가 요약한 데일리 뉴스 리포트 HTML (장전/장중/장후/주말)
├── 데일리뉴스*.py                # 뉴스 크롤러 봇 스크립트들
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
  - 최종 정제된 데이터를 `master_schedule_db.csv`에 덮어쓰고, 투자 일정 대시보드인 `schedule.html`을 렌더링한 후 GitHub에 배포합니다.
- **`generate_index.py`**:
  - 데일리 뉴스 파이프라인에서 생성된 `reports/` 리포트들과 `master_schedule_db.csv`의 단기 일정을 읽어옵니다.
  - 메인 포털 화면인 `index.html`을 생성합니다. 
- **`agents/*`**:
  - 각각의 외부 소스(DART 공시, FRED 매크로 API, 정부 부처 RSS, 예탁결제원 PDF 등)에 맞게 특화된 파싱 로직을 담당합니다. 자세한 목록은 `AGENTS.md`를 참고하세요.

## 4. 데이터 흐름 (Data Flow)
1. **[Trigger]**: 크론잡(Cron-job.org / Launchd)이 지정된 시간(예: 05:30, 11:30, 17:30, 23:30)에 백그라운드에서 스크립트를 실행합니다.
2. **[Scraping]**: `schedule_orchestrator.py`가 각 `agent/*.py`를 호출하여 외부 웹/API/PDF에서 Raw Data를 긁어옵니다.
3. **[Processing & NLP]**: 수집된 데이터 중 중복되는 뉴스나 공시는 AI 텍스트 임베딩(Cosine Similarity)을 통해 제거하고, 날짜 포맷(`YYYY-MM-DD`)을 통일합니다.
4. **[Storage]**: 최종 데이터를 `master_schedule_db.csv` 와 `vip_momentum_alerts.csv` 에 저장(Overwrite)합니다.
5. **[Rendering]**: 
   - 오케스트레이터가 `schedule.html`을 즉시 렌더링합니다.
   - (메인 페이지 배포 스케줄일 경우) `generate_index.py`가 작동하여 `index.html`을 렌더링합니다.
6. **[Deploy]**: 변경된 파일(CSV, HTML)을 `git commit & push` 하여 GitHub Pages 등의 라이브 서버에 반영시킵니다.

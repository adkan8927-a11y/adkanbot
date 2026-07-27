# Dynamic Keyword Optimization & Auto-Pruning System (Feedback & Implementation Plan)

주식 시장의 주도 테마 및 수급 이동(거래대금 150억+ / 상한가 / 신규 호재)을 민첩하게 포착하고, 시장에서 소멸된 옛날 키워드(노이즈)를 자동으로 솎아내어 뉴스 수집의 정확도와 요약 품질을 극대화하는 동적 키워드 관리 파이프라인 계획입니다.

## 💡 시스템 구조 및 핵심 메커니즘

- **키워드 성과 추적기 (`keyword_analytics.csv`)**: 뉴스 수집기(`장전`, `장후`, `주말`)가 구동될 때마다 키워드별 매칭 성과 로그 기록.
- **신규 주도재료 자동 포착기 (Local Ollama LLM)**: 네이버 증권 거래대금 150억 이상 / 상한가 종목 헤드라인을 수집하여 로컬 Ollama LLM (`gemma4:e4b`)으로 신규 주도 테마 키워드 20~30개 추출.
- **노이즈 가지치기 엔진 (Stale Keyword Pruner)**: 최근 14~30일간 매칭 건수 0건인 옛날 테마 키워드 자동 솎아내기 (안전 백업 `키워드3_backup_YYYYMMDD.json` 포함).
- **중앙 키워드 제어 에이전트 (`keyword_manager.py`)**: 분석(`--analyze`), 신규 발굴(`--discover`), 가지치기(`--prune`), 동기화(`--sync`) CLI 에이전트.

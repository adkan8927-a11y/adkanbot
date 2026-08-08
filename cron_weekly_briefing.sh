#!/bin/bash
# ====================================================================
# 🚀 주말 5대 핵심 섹터 위클리 브리핑 자동 발행 스크립트
# macOS launchd / crontab 용 (매주 일요일 오전 9시 실행)
# ====================================================================
# 설치 방법 (아래 둘 중 택 1):
#
# [방법 1] crontab 등록:
#   crontab -e
#   0 9 * * 0 /Users/adkan/adkan연구2/cron_weekly_briefing.sh >> /Users/adkan/adkan연구2/logs/cron_weekly.log 2>&1
#
# [방법 2] launchd plist:
#   아래 별도 plist 파일 참고 (com.adkan.weekly-briefing.plist)
# ====================================================================

set -euo pipefail

# 환경 변수
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
PROJ_DIR="/Users/adkan/adkan연구2"
LOG_DIR="$PROJ_DIR/logs"
TODAY=$(date +"%Y-%m-%d")

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

echo "========================================"
echo "📊 위클리 브리핑 자동 발행 시작: $TODAY"
echo "========================================"

cd "$PROJ_DIR"

# .env 로드 (KIS API 키 등)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 1. 5대 섹터 위클리 브리핑 파이프라인 실행 (gemma4:e4b LLM 추론 포함)
echo "🔄 [STEP 1] 5대 섹터 위클리 브리핑 파이프라인 실행..."
python3 "$PROJ_DIR/run_sector_report_pipeline.py" --date "$TODAY"

# 2. 결과물 확인
MD_FILE="$PROJ_DIR/reports/${TODAY}_위클리브리핑.md"
HTML_FILE="$PROJ_DIR/reports/${TODAY}_위클리브리핑.html"

if [ -f "$MD_FILE" ] && [ -f "$HTML_FILE" ]; then
    echo "📋 [STEP 2] 리포트 파일 생성 성공"
else
    echo "❌ 리포트 파일 생성 실패! 파이프라인 로그를 확인하세요."
    exit 1
fi

# 3. index.html 대시보드 재빌드
echo "🔧 [STEP 3] 메인 대시보드 index.html 재빌드..."
python3 generate_index.py

# 4. GitHub Pages 배포 (git push)
echo "🚀 [STEP 4] GitHub Pages 배포..."
git add -A
git commit -m "auto: ${TODAY} 위클리 브리핑 발행" || echo "변경사항 없음 (커밋 스킵)"
git push origin main || echo "⚠️ git push 실패 (네트워크 확인 필요)"

echo "========================================"
echo "✅ 위클리 브리핑 자동 발행 완료: $TODAY"
echo "========================================"

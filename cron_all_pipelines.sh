#!/bin/bash
# ============================================================
# 🤖 adkan연구3 통합 자동화 스케줄러 (cron_all_pipelines.sh)
# ============================================================

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/adkan/Library/Python/3.9/bin:$PATH"

MODE=$1
CDIR="/Users/adkan/adkan연구3"
cd "$CDIR" || exit 1
mkdir -p logs

# 깃허브 충돌 방지 git pull --rebase
cd /Users/adkan/adkan연구2 && git pull --rebase origin main >> "$CDIR/logs/cron_git.log" 2>&1
cd "$CDIR"

case "$MODE" in
    "premarket_check")
        echo "⏰ [08:50] 장전 1차 악재 및 일정 스캔 가동..."
        /usr/bin/python3 trade_agent.py --mode premarket_check --send-telegram >> logs/cron_trade_premarket_check.log 2>&1
        ;;
    "premarket_order"|"premarket")
        echo "⏰ [08:57] 장전 2차 동시호가 매수 집행 가동..."
        /usr/bin/python3 trade_agent.py --mode premarket_order --send-telegram >> logs/cron_trade_premarket_order.log 2>&1
        ;;
    "screening")
        echo "⏰ [15:10] 장마감 스크리닝 파이프라인 가동..."
        /usr/bin/python3 run_screening_pipeline.py >> logs/cron_screening.log 2>&1
        ;;
    "closing")
        echo "⏰ [15:25] 종가베팅 매수 예약 집행 가동..."
        /usr/bin/python3 trade_agent.py --mode closing --send-telegram >> logs/cron_trade_closing.log 2>&1
        ;;
    "surge")
        echo "⏰ [16:30] 당일 상한가/급등주 분석 리포트 가동..."
        /usr/bin/python3 run_daily_surge_report_pipeline.py --max-upper 5 --max-surge 10 >> logs/cron_surge.log 2>&1
        ;;
    "feedback")
        echo "⏰ [18:00] 성과 피드백 리포트 파이프라인 가동..."
        /usr/bin/python3 run_feedback_pipeline.py >> logs/cron_feedback.log 2>&1
        ;;
    *)
        echo "Usage: $0 {premarket|screening|closing|surge|feedback}"
        exit 1
        ;;
esac

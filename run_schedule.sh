#!/bin/bash
# 퀀트 투자일정 및 VIP 모멘텀 에이전트 통합 로컬 스케줄링 쉘

# 1. 작업 디렉토리 이동
cd "/Users/adkan/adkan연구2"

# 2. 실행 로그에 타임스탬프 기록
echo "==========================================" >> local_schedule_run.log
echo "⏰ 실행 시각: $(date '+%Y-%m-%d %H:%M:%S')" >> local_schedule_run.log
echo "==========================================" >> local_schedule_run.log

# 3. 환경 변수 설정
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# 4. VIP 모멘텀 에이전트 실행 (로컬 Ollama 필요)
echo "🤖 [1/2] VIP 모멘텀 에이전트 수집 및 로컬 LLM 분석 시작..." >> local_schedule_run.log
/usr/bin/python3 "schedule check/agents/vip_momentum_agent.py" >> local_schedule_run.log 2>&1

# 5. 오케스트레이터 파이프라인 가동 (일정 병합, HTML 빌드 및 Git 배포)
echo "🚀 [2/2] 일정 파이프라인 가동 및 대시보드 빌드/Git 배포 시작..." >> local_schedule_run.log
/usr/bin/python3 "schedule check/schedule_orchestrator.py" >> local_schedule_run.log 2>&1

echo "✅ 전체 일정 파이프라인 수집 및 배포 완료!" >> local_schedule_run.log

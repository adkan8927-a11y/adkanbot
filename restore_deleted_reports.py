#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
복구 및 대시보드 재배포 자동화 스크립트 (restore_deleted_reports.py)

사용법:
  python3 restore_deleted_reports.py [YYYY-MM-DD]

예시:
  python3 restore_deleted_reports.py 2026-09-29
  python3 restore_deleted_reports.py            (날짜 미입력 시 오늘 날짜 자동 지정)
"""

import sys
import os
import re
import glob
import subprocess
from datetime import datetime

def run_cmd(cmd, check=True):
    """쉘 명령어를 실행하고 결과를 반환합니다."""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"❌ 명령어 실행 실패 (코드 {res.returncode}): {res.stderr.strip()}")
    return res

def get_latest_commit_for_file(filepath):
    """해당 파일이 존재했던 가장 최신 커밋 해시를 탐색합니다."""
    res = run_cmd(f'git log --all --full-history -n 1 --pretty=format:"%H" -- "{filepath}"', check=False)
    commit = res.stdout.strip()
    return commit if commit else None

def restore_reports_for_date(date_str):
    print(f"\n==========================================")
    print(f"🔄 [{date_str}] 삭제된 보고서/차트 복원 및 배포 자동화")
    print(f"==========================================\n")

    compact_date = date_str.replace("-", "")
    
    restored_count = 0

    # 1. 깃 히스토리에서 해당 날짜에 생성되었던 차트 이미지 목록 탐색
    chart_res = run_cmd(f'git log --all --full-history --name-only --pretty="" -- "charts/*{compact_date}*" "charts/*{date_str}*"', check=False)
    chart_files = list(set([line.strip() for line in chart_res.stdout.splitlines() if line.strip().startswith("charts/")]))

    for chart_file in chart_files:
        commit = get_latest_commit_for_file(chart_file)
        if commit:
            checkout_res = run_cmd(f'git checkout {commit} -- "{chart_file}"', check=False)
            if checkout_res.returncode == 0:
                print(f"✅ 복원 완료 (차트): {chart_file}")
                restored_count += 1

    # 2. 깃 히스토리 전체에서 해당 날짜의 reports/ 파일들 탐색
    report_res = run_cmd(f'git log --all --full-history --name-only --pretty="" -- "reports/{date_str}*" "reports/*/{date_str}*"', check=False)
    report_files = list(set([line.strip() for line in report_res.stdout.splitlines() if line.strip().startswith("reports/")]))

    for report_file in report_files:
        commit = get_latest_commit_for_file(report_file)
        if commit:
            checkout_res = run_cmd(f'git checkout {commit} -- "{report_file}"', check=False)
            if checkout_res.returncode == 0:
                print(f"✅ 복원 완료 (보고서): {report_file}")
                restored_count += 1

    if restored_count == 0:
        print(f"⚠️ [{date_str}] 날짜에 해당하는 복원 대상 보고서/차트가 이미 최신 상태이거나 깃 히스토리에 존재하지 않습니다.")
    else:
        print(f"\n🎉 총 {restored_count}개 복원 대상 파일 수용 완료!")

    # 3. 메인 대시보드 (index.html) 재빌드
    print("\n🔨 메인 대시보드 (index.html) 재빌드 진행 중...")
    try:
        from generate_index import generate_index
        generate_index()
        print("✅ index.html 대시보드 재빌드 성공!")
    except Exception as e:
        print(f"⚠️ generate_index 직접 실행 중: {e}")
        run_cmd("python3 generate_index.py")

    # 4. Git commit & push (원격 자동 커밋 충돌 시 자동 리베이스 & 재시도)
    print("\n🚀 Git Commit 및 GitHub Pages 배포 진행 중...")
    run_cmd("git add .")
    run_cmd(f'git commit -m "docs: Restore {date_str} reports & rebuild index.html dashboard"', check=False)
    
    max_retries = 3
    pushed = False
    for attempt in range(max_retries):
        push_res = run_cmd("git push origin main", check=False)
        if push_res.returncode == 0:
            pushed = True
            break
        print(f"🔄 원격 변경사항(자동 커밋) 동기화 시도 중 ({attempt + 1}/{max_retries})...")
        run_cmd("git fetch origin main", check=False)
        rebase_res = run_cmd("GIT_EDITOR=true git rebase origin/main", check=False)
        
        # 리베이스 중 index.html 충돌 발생 시 자동 해결
        while rebase_res.returncode != 0:
            print("⚠️ Rebase 충돌 감지, index.html 재빌드 후 리베이스 계속 진행...")
            run_cmd("git rm -f docs_cache/opendartreader_corp_codes_*.pkl 2>/dev/null", check=False)
            run_cmd("python3 generate_index.py", check=False)
            run_cmd("git add .", check=False)
            rebase_res = run_cmd("GIT_EDITOR=true git rebase --continue", check=False)

    if pushed:
        print("\n✨ [성공] 삭제된 보고서 복원, 대시보드 갱신 및 GitHub Pages 배포가 완벽하게 완료되었습니다!")
    else:
        print("\n⚠️ Push 실패: 최신 깃 상태 확인 필요")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_date = sys.argv[1].strip()
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
        print(f"💡 날짜 인자가 입력되지 않아 오늘 날짜({target_date})로 자동 지정을 시작합니다.")

    restore_reports_for_date(target_date)

"""
설정 파일 (config.py)
3대 핵심 매매 전략 조건 변수 및 시스템 설정값 관리
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# 기본 디렉토리 설정
OUTPUT_CHART_DIR = BASE_DIR / "charts"
os.makedirs(OUTPUT_CHART_DIR, exist_ok=True)

# API & 텔레그램 설정
KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")
KIS_IS_VIRTUAL = os.getenv("KIS_IS_VIRTUAL", "true").lower() == "true"
KIS_CANO = os.getenv("KIS_CANO", "")
KIS_ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD", "01")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 공통 시장 선택 및 공통 이동평균선 연산 대상
TARGET_MARKET = 'KRX'
MA_PERIODS = [3, 5, 8, 13, 20, 60, 120, 240]
UPPER_LIMIT_PCT = 29.5
MIN_TRADING_VALUE = 100_000_000_000


# --- [ 전략 1: 양음양 & 사윗감 매매 설정 ] ---
STRATEGY1_MIN_AMOUNT = 50_000_000_000  # 기준일 거래대금 최소 500억 원
STRATEGY1_MIN_PCT = 15.0               # 기준일 최소 등락률 +15%
STRATEGY1_LOOKBACK = 5                 # 조정 음봉 관찰 기간 (최대 5일)

# --- [ 전략 2: 매집봉 & 이일홍 기법 설정 ] ---
STRATEGY2_VOLUME_MULT = 5.0            # 평소 대비 거래량 500% 이상 (매집봉)
STRATEGY2_LOOKBACK = 40                # 매집봉 이후 조정 관찰 기간 (최대 40일)

# --- [ 전략 3: 수급 & 핥 기법 설정 ] ---
STRATEGY3_BOTTOM_PCT = 66.0            # 52주 최고가 대비 66% 이하 (바닥권 완화)
STRATEGY3_MAJOR_BUY = 10_000_000_000   # 최근 20일 외인/기관 순매수 100억 이상
STRATEGY3_ETC_CORP_AMT = 1_000_000_000 # 최근 5일 기타법인 순매수 10억 이상
STRATEGY3_ETC_CORP_QTY = 50_000        # 최근 5일 기타법인 순매수 5만주 이상

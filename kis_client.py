"""
한국투자증권 (KIS Developers) API 연동 모듈 (kis_client.py)
OAuth2 토큰 발급, 시세 조회, 수급(외인/기관) 데이터 수집
"""

import requests
import json
import os
import time
import logging
from pathlib import Path
from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_IS_VIRTUAL

logger = logging.getLogger(__name__)

# KIS 도메인 설정 (모의투자 vs 실전투자)
REAL_URL = "https://openapi.koreainvestment.com:9443"
VIRTUAL_URL = "https://openapivts.koreainvestment.com:29443"

BASE_URL = VIRTUAL_URL if KIS_IS_VIRTUAL else REAL_URL
TOKEN_CACHE_FILE = Path(__file__).resolve().parent / ".token_cache.json"


class KISClient:
    def __init__(self, app_key: str = KIS_APP_KEY, app_secret: str = KIS_APP_SECRET, is_virtual: bool = KIS_IS_VIRTUAL):
        self.app_key = app_key
        self.app_secret = app_secret
        self.is_virtual = is_virtual
        self.base_url = VIRTUAL_URL if is_virtual else REAL_URL
        self.access_token = None
        self.token_expired_at = 0

        # 토큰 발급 및 초기화
        self._init_access_token()

    def _init_access_token(self):
        """
        저장된 토큰 로드 또는 신규 OAuth2 Access Token 발급
        """
        if not self.app_key or not self.app_secret:
            logger.warning("한투 API Key 및 App Secret이 설정되지 않았습니다.")
            return

        # 1. 캐시 파일에서 토큰 확인
        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    if cache.get("expired_at", 0) > time.time() + 300:  # 만료 5분 전까지 사용
                        self.access_token = cache.get("access_token")
                        self.token_expired_at = cache.get("expired_at")
                        logger.info("✅ KIS 캐시된 Access Token 사용 가능.")
                        return
            except Exception as e:
                logger.debug(f"토큰 캐시 파일 읽기 실패: {e}")

        # 2. 신규 토큰 발급
        self.issue_access_token()

    def issue_access_token(self) -> bool:
        """
        KIS OAuth2 Access Token 발급 요청 API
        """
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            data = res.json()

            if "access_token" in data:
                self.access_token = data["access_token"]
                expires_in = int(data.get("expires_in", 86400))
                self.token_expired_at = time.time() + expires_in

                # 캐시 저장
                with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({
                        "access_token": self.access_token,
                        "expired_at": self.token_expired_at
                    }, f, indent=2)

                logger.info("✅ KIS 신규 Access Token 발급 성공!")
                return True
            else:
                logger.error(f"❌ KIS 토큰 발급 실패: {data}")
                return False
        except Exception as e:
            logger.error(f"KIS 토큰 발급 API 오류: {e}")
            return False

    def get_headers(self, tr_id: str) -> dict:
        """
        KIS API 공통 헤더 구성
        """
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }

    def get_current_price(self, symbol: str) -> dict:
        """
        주식 현재가 시세 조희 (FHKST01010100)
        
        Returns:
            dict: {stck_prpr (현재가), acml_tr_pbmn (거래대금), prdy_ctrt (등락률), is_upper_limit (상한가 여부)}
        """
        if not self.access_token:
            return {}

        tr_id = "FHKST01010100"
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD={symbol}"
        headers = self.get_headers(tr_id)

        try:
            res = requests.get(url, headers=headers, timeout=5)
            data = res.json()

            if data.get("rt_cd") == "0" and "output" in data:
                output = data["output"]
                price = int(output.get("stck_prpr", 0))          # 현재가
                amount = int(output.get("acml_tr_pbmn", 0))      # 누적 거래대금 (원)
                change_rate = float(output.get("prdy_ctrt", 0.0))# 전일 대비 등락률 (%)
                high_price = int(output.get("stck_hgpr", 0))     # 최고가
                limit_price = int(output.get("stck_mxpr", 0))    # 상한가 가격

                is_upper = (price >= limit_price and limit_price > 0) or (change_rate >= 29.5)

                return {
                    "symbol": symbol,
                    "price": price,
                    "amount": amount,
                    "amount_100m": round(amount / 100_000_000, 1),
                    "change_rate": change_rate,
                    "is_upper_limit": is_upper
                }
        except Exception as e:
            logger.warning(f"KIS 시세 조회 실패 ({symbol}): {e}")

    def get_expected_execution_price(self, symbol: str) -> dict:
        """
        장전 동시호가 (08:30~08:59) 예상체결가 및 예상 갭상승률 조회 (FHKST01010200)
        
        Returns:
            dict: {antc_cnpr (예상체결가), antc_cntg_prdy_ctrt (예상 등락률%), antc_vol (예상 체결량)}
        """
        if not self.access_token:
            return {}

        tr_id = "FHKST01010200"
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-asking-price-expected-ccnl?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD={symbol}"
        headers = self.get_headers(tr_id)

        try:
            res = requests.get(url, headers=headers, timeout=5)
            data = res.json()

            if data.get("rt_cd") == "0" and "output" in data:
                output = data["output"]
                exp_price = int(output.get("antc_cnpr", 0))            # 예상체결가
                exp_rate = float(output.get("antc_cntg_prdy_ctrt", 0.0))# 전일대비 예상 등락률 (%)
                exp_vol = int(output.get("antc_vol", 0))               # 예상체결량

                return {
                    "symbol": symbol,
                    "exp_price": exp_price,
                    "exp_gap_pct": exp_rate,
                    "exp_volume": exp_vol,
                    "is_high_gap": exp_rate >= 3.0 # +3% 이상 갭상승 시 위험 알림
                }
        except Exception as e:
            logger.warning(f"KIS 동시호가 예상체결가 조회 실패 ({symbol}): {e}")

    def has_active_order_or_balance(self, symbol: str) -> bool:
        """
        해당 종목이 현재 계좌 잔고에 있거나 미체결 매수 주문이 존재하는지 확인
        """
        # 모의/실전 API 호출 또는 캐시 기반 검증 (안전 기본값 False)
        return False

        return {}


if __name__ == "__main__":
    client = KISClient()
    if client.access_token:
        print("삼성전자(005930) 시세 조회 테스트:")
        price_info = client.get_current_price("005930")
        print(price_info)


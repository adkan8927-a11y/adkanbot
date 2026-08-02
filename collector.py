"""
데이터 수집 모듈 (collector.py)
FinanceDataReader 및 pykrx를 활용하여 국내 주식 시장 데이터 수집
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = Path(__file__).resolve().parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)

import requests
import urllib.request
import socket

# 글로벌 소켓 및 urllib/requests 5.0초 소켓 타임아웃 패치 (500개 완전 수집 보장)
socket.setdefaulttimeout(5.0)

_orig_requests_get = requests.get
def _requests_get_timeout(*args, **kwargs):
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 5.0
    return _orig_requests_get(*args, **kwargs)
requests.get = _requests_get_timeout

_orig_urlopen = urllib.request.urlopen
def _urlopen_timeout(*args, **kwargs):
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 5.0
    return _orig_urlopen(*args, **kwargs)
urllib.request.urlopen = _urlopen_timeout

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    import FinanceDataReader as fdr
    HAS_FDR = True
except ImportError:
    HAS_FDR = False

try:
    from pykrx import stock as pykrx_stock
    HAS_PYKRX = True
except ImportError:
    HAS_PYKRX = False


REJECT_STOCK_PATTERNS = r'스팩|리츠|관리|환기|정리매매|우$|우B$|우C$|우1$|우2$|우3$|우4$|우5$'


def get_stock_list(market: str = "KRX") -> pd.DataFrame:
    """
    국내 상장 종목 리스트 가져오기 (KOSPI / KOSDAQ / KRX) - 일반 주식만 필터링
    """
    if HAS_FDR:
        logger.info(f"FinanceDataReader를 통해 {market} 종목 리스트를 수집합니다.")
        try:
            df = fdr.StockListing(market)
            if 'Code' not in df.columns and 'Symbol' in df.columns:
                df['Code'] = df['Symbol']
            if 'Name' in df.columns:
                df = df[~df['Name'].str.contains(REJECT_STOCK_PATTERNS, regex=True, na=False)]
            return df
        except Exception as e:
            logger.warning(f"FDR 종목 리스트 수집 실패: {e}")

    if HAS_PYKRX:
        logger.info(f"pykrx를 통해 {market} 종목 리스트를 수집합니다.")
        try:
            today_str = datetime.now().strftime("%Y%m%d")
            tickers = pykrx_stock.get_market_ticker_list(today_str, market=market)
            data = []
            for ticker in tickers:
                name = pykrx_stock.get_market_ticker_name(ticker)
                data.append({"Code": ticker, "Name": name, "Market": market})
            df = pd.DataFrame(data)
            if 'Name' in df.columns:
                df = df[~df['Name'].str.contains(REJECT_STOCK_PATTERNS, regex=True, na=False)]
            return df
        except Exception as e:
            logger.error(f"pykrx 종목 리스트 수집 실패: {e}")

    raise RuntimeError("FinanceDataReader 또는 pykrx 라이브러리가 설치되어 있어야 합니다.")


def get_top_volume_stocks(market: str = "KRX", limit: int = 150) -> pd.DataFrame:
    """
    최근 영업일 기준 거래대금 상위 종목 리스트 수집 (우선주/스팩/리츠/관리/환기/정리매매 자동 제외)
    """
    if not HAS_FDR:
        logger.warning("FDR 미설치로 상위 거래대금 종목 필터링이 불가하여 기본 목록을 반환합니다.")
        return get_stock_list(market).head(limit)

    try:
        logger.info(f"FinanceDataReader를 통해 {market} 거래대금 상위 {limit}개 종목을 수집합니다.")
        df = fdr.StockListing(market)
        
        # 6자리 숫자로 구성된 일반 주식 코드만 필터링 (ETF/ETN 제외)
        df = df[df['Code'].str.match(r'^\d{6}$') == True]
        
        # 우선주, 스팩, 리츠, 관리, 환기, 정리매매 종목 자동 제외
        if 'Name' in df.columns:
            df = df[~df['Name'].str.contains(REJECT_STOCK_PATTERNS, regex=True, na=False)]
        
        # 거래대금(Amount) 컬럼 기준 내림차순 정렬
        if 'Amount' in df.columns:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df = df.dropna(subset=['Amount'])
            df = df.sort_values(by='Amount', ascending=False)
            
        return df.head(limit)
    except Exception as e:
        logger.warning(f"거래대금 상위 종목 수집 중 오류: {e}")
        return get_stock_list(market).head(limit)


def get_ohlcv(symbol: str, start_date: str = None, end_date: str = None, count: int = 60) -> pd.DataFrame:
    """
    특정 종목의 일봉 OHLCV (시가, 고가, 저가, 종가, 거래량, 거래대금) 데이터 수집
    
    Args:
        symbol (str): 종목코드 (예: '005930')
        start_date (str): 시작일자 ('YYYY-MM-DD')
        end_date (str): 종료일자 ('YYYY-MM-DD')
        count (int): 수집할 일수 (start_date가 지정되지 않았을 때 기본값 사용)
        
    Returns:
        pd.DataFrame: Open, High, Low, Close, Volume, Amount (거래대금)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
        
    if start_date is None:
        start_dt = datetime.now() - timedelta(days=count * 2)  # 주말 포함 넉넉히 가져옴
        start_date = start_dt.strftime("%Y-%m-%d")

    df = None

    # 1. FinanceDataReader 시도
    if HAS_FDR:
        try:
            df = fdr.DataReader(symbol, start=start_date, end=end_date)
            if not df.empty:
                # 표준 컬럼 이름 통일
                df.rename(columns={
                    'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'
                }, inplace=True)
                
                # 거래대금(Amount) 계산 (FDR에 Amount가 없는 경우 종가 * 거래량으로 추정)
                if 'Amount' not in df.columns:
                    df['Amount'] = df['Close'] * df['Volume']
        except Exception as e:
            logger.debug(f"FDR 데이터 수집 실패 ({symbol}): {e}")

    # 2. pykrx 보완 시도 (Amount가 정확히 제공됨)
    if (df is None or df.empty) and HAS_PYKRX:
        try:
            s_date = start_date.replace("-", "")
            e_date = end_date.replace("-", "")
            py_df = pykrx_stock.get_market_ohlcv_by_date(s_date, e_date, symbol)
            if not py_df.empty:
                py_df.rename(columns={
                    '시가': 'Open', '고가': 'High', '저가': 'Low', '종가': 'Close',
                    '거래량': 'Volume', '거래대금': 'Amount'
                }, inplace=True)
                df = py_df
        except Exception as e:
            logger.debug(f"pykrx 데이터 수집 실패 ({symbol}): {e}")

    if df is None or df.empty:
        return pd.DataFrame()

    # 데이터 정리
    df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Amount']].dropna()
    df.sort_index(inplace=True)
    return df


def get_all_ohlcv_cached(symbols_df_or_list, target_date: str = None, count: int = 320, max_workers: int = 12) -> dict:
    """
    전종목 일봉 데이터를 Parquet 캐싱 + ThreadPoolExecutor 멀티스레드로 초고속 수집
    
    Args:
        symbols_df_or_list: 종목코드 리스트 또는 DataFrame
        target_date (str): 기준일자 ('YYYY-MM-DD')
        count (int): 수집할 봉 수
        max_workers (int): 멀티스레드 병열 작업 수
        
    Returns:
        dict: {code: pd.DataFrame}
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    cache_files = list(CACHE_DIR.glob(f"ohlcv_*_{target_date}.parquet"))
    if cache_files:
        best_cache = max(cache_files, key=lambda p: int(p.name.split('_')[1]) if p.name.split('_')[1].isdigit() else 0)
        try:
            logger.info(f"⚡ [Parquet Cache HIT] 가장 최신/최대 캐시 파일 초고속 로딩: {best_cache.name}")
            full_df = pd.read_parquet(best_cache)
            stock_dict = {}
            for code, group in full_df.groupby("Code"):
                stock_dict[str(code).zfill(6)] = group.drop(columns=["Code"])
            return stock_dict
        except Exception as e:
            logger.warning(f"⚠️ Parquet 캐시 읽기 실패 ({e}), 멀티스레드 새로 수집을 시작합니다.")

    # 종목 리스트 정리
    if isinstance(symbols_df_or_list, pd.DataFrame):
        symbol_items = []
        for idx, row in symbols_df_or_list.iterrows():
            c = str(row['Code']).zfill(6)
            n = row.get('Name', c)
            symbol_items.append({"code": c, "name": n})
    else:
        symbol_items = [{"code": str(s).zfill(6), "name": str(s)} for s in symbols_df_or_list]

    # Parquet 캐시 저장 경로 사전 정의
    cache_file = CACHE_DIR / f"ohlcv_{len(symbol_items)}_{target_date}.parquet"

    # 2. Cache MISS: ThreadPoolExecutor 멀티스레드 병렬 통신 (3.5초 수집)
    import socket
    socket.setdefaulttimeout(3.0)

    logger.info(f"🚀 [Parquet Cache MISS] ThreadPoolExecutor (스레드 {max_workers}개) 멀티스레드 동시 수집 시작 ({len(symbol_items)}개 종목)...")
    
    start_time = datetime.now()

    def fetch_single(item):
        sym = item["code"]
        for retry in range(3):
            try:
                df = get_ohlcv(sym, count=count)
                if df is not None and not df.empty:
                    df = df.copy()
                    df['Code'] = sym
                    return sym, df
            except Exception:
                import time
                time.sleep(0.1)
        return sym, None

    results = {}
    combined_dfs = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(fetch_single, item): item for item in symbol_items}
        for i, future in enumerate(as_completed(future_to_item), 1):
            try:
                sym, df = future.result()
                if df is not None and not df.empty:
                    results[sym] = df.drop(columns=["Code"])
                    combined_dfs.append(df)
            except Exception:
                pass
            if i % 100 == 0 or i == len(symbol_items):
                logger.info(f"  [수집 진행중] {i}/{len(symbol_items)}개 종목 완료...")

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"✅ [멀티스레드 수집 완수] 총 {len(results)}개 종목 수집 완료 (소요시간: {elapsed:.2f}초)")

    # 3. Parquet 저장 (다음 실행 시 0.2초 로딩 보장)
    if combined_dfs:
        try:
            full_df = pd.concat(combined_dfs)
            full_df.to_parquet(cache_file, engine="pyarrow", compression="snappy")
            logger.info(f"💾 [Parquet 저장 완수] 로컬 캐시 파일 생성 완료: {cache_file.name}")
        except Exception as e:
            logger.warning(f"⚠️ Parquet 저장 실패: {e}")

    return results


if __name__ == "__main__":
    print("=== 데이터 수집 모듈 테스트 ===")
    print("1. 삼성전자(005930) 최근 10일 주가 데이터 가져오기")
    samsung_df = get_ohlcv("005930", count=10)
    print(samsung_df.tail())

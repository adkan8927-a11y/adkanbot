"""
3대 매매 전략 스크리너 엔진 (screener.py)

1. 전략 1: 양음양 & 사윗감 매매 (3, 5, 8, 13, 20일선 지지)
2. 전략 2: 매집봉 & 이일홍 기법 (20/120/240일선 밀집 수렴 돌파)
3. 전략 3: 수급 & 핥 기법 (52주 바닥 + 외인/기관 100억 + 기타법인 수급 + 이평선 핥기)
"""

import pandas as pd
import numpy as np
import logging
import re
from config import (
    MIN_TRADING_VALUE, UPPER_LIMIT_PCT, MA_PERIODS,
    STRATEGY1_MIN_AMOUNT, STRATEGY1_MIN_PCT, STRATEGY1_LOOKBACK,
    STRATEGY2_VOLUME_MULT, STRATEGY2_LOOKBACK,
    STRATEGY3_BOTTOM_PCT, STRATEGY3_MAJOR_BUY, STRATEGY3_ETC_CORP_AMT, STRATEGY3_ETC_CORP_QTY
)

logger = logging.getLogger(__name__)

REJECT_NAME_PATTERNS = [
    r'스팩', r'리츠', r'관리', r'환기', r'정리매매',
    r'우$', r'우B$', r'우C$', r'우1$', r'우2$', r'우3$', r'우4$', r'우5$'
]

def is_valid_trading_stock(name: str, code: str, df: pd.DataFrame = None) -> bool:
    """
    유저 지정 제외 종목 필터링:
    1. 제외: 우선주, 관리종목(환기, 상장폐지/정리매매), 스팩, 리츠
    2. 제외: 거래정지 종목 (당일 거래량 == 0 또는 거래대금 == 0)
    3. 제외: 단일가거래 종목 (당일 거래 정체 상태)
    4. 포함: 투자경고, 투자주의, 투자위험 종목 (정상 거래 가능 시 100% 포함!)
    """
    if name:
        for pat in REJECT_NAME_PATTERNS:
            if re.search(pat, name):
                return False

    if df is not None and not df.empty and len(df) >= 1:
        latest = df.iloc[-1]
        volume = latest.get("Volume", 0)
        amount = latest.get("Amount", 0)
        if volume == 0 or amount == 0:
            return False

    return True


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    이동평균선 (3, 5, 8, 13, 20, 60, 120, 240일선) 추가
    """
    df = df.copy()
    
    # 이동평균선 계산
    for p in MA_PERIODS:
        df[f'MA_{p}'] = df['Close'].rolling(window=p).mean()

    # 3일선, 5일선 이격도(%) 계산: (종가 / 이동평균선 - 1) * 100
    if 'MA_3' in df.columns:
        df['Disparity_MA3'] = ((df['Close'] / df['MA_3']) - 1) * 100
    if 'MA_5' in df.columns:
        df['Disparity_MA5'] = ((df['Close'] / df['MA_5']) - 1) * 100

    return df


def screen_adk_special(df: pd.DataFrame) -> dict:
    """
    ★ ADK특 (양음양 13~20일선 핵심 반등 전용 조건검색 엔진)
    유저 지정 절대 수칙식 (원문 1:1 보장):
    A and B and !C and D and !E and (F or G) and !H and !I and !J and !K and !L and !M and N
    """
    if df.empty or len(df) < 60:
        return None

    df_ind = df.copy()
    if 'Amount' not in df_ind.columns:
        df_ind['Amount'] = df_ind['Close'] * df_ind['Volume']

    # 이동평균선
    df_ind['MA1'] = df_ind['Close']
    df_ind['MA5'] = df_ind['Close'].rolling(5).mean()
    df_ind['MA13'] = df_ind['Close'].rolling(13).mean()
    df_ind['MA20'] = df_ind['Close'].rolling(20).mean()
    df_ind['MA60'] = df_ind['Close'].rolling(60).mean()
    df_ind['MA120'] = df_ind['Close'].rolling(120).mean()
    df_ind['MA224'] = df_ind['Close'].rolling(224).mean() if len(df_ind) >= 224 else np.nan
    df_ind['MA448'] = df_ind['Close'].rolling(448).mean() if len(df_ind) >= 448 else np.nan

    # Envelope(13,6)
    df_ind['Env_Upper'] = df_ind['MA13'] * 1.06
    df_ind['Env_Lower'] = df_ind['MA13'] * 0.94

    r0 = df_ind.iloc[-1] # 0봉전
    r1 = df_ind.iloc[-2] # 1봉전
    r2 = df_ind.iloc[-3] # 2봉전

    # A: [일] 0봉전 (종가 5)이평 하락+보합추세유지 2회 이상
    a_pass = (r0['MA5'] <= r1['MA5']) and (r1['MA5'] <= r2['MA5'])

    # B: [일] 0봉전 Envelope(13,6) 종가가 Envelope 상한선이상 5봉이내 1회이상
    b_pass = any(df_ind['Close'].tail(5) >= df_ind['Env_Upper'].tail(5))

    # C: [일] 0봉전 Envelope(13,6) 종가가 Envelope 하한선이하 13봉이내 2회이상
    c_count = (df_ind['Close'].tail(13) <= df_ind['Env_Lower'].tail(13)).sum()
    c_pass = (c_count >= 2)

    # D: 20봉 이내 거래대금 40,000백만원(400억원) 이상 1회 이상
    d_pass = (df_ind['Amount'].tail(20).max() >= 40_000_000_000)

    # E: [일] 0봉전 단순(종가 1)이평이 단순(종가 13)이평을 13봉이내 데드크로스 1회이상
    e_pass = False
    for k in range(1, 14):
        if k < len(df_ind):
            rk0 = df_ind.iloc[-k]
            rk1 = df_ind.iloc[-k-1] if (k+1) <= len(df_ind) else rk0
            if (rk1['Close'] >= rk1['MA13']) and (rk0['Close'] < rk0['MA13']):
                e_pass = True
                break

    # F: [일] 0봉전 저가대비 0봉전 시가등락률 3%이상
    f_pass = (r0['Low'] > 0) and (((r0['Open'] - r0['Low']) / r0['Low']) >= 0.03)

    # G: [일] 0봉전 시가 == 0봉전 저가
    g_pass = (r0['Open'] == r0['Low'])

    # H: 상장일 298일 이내
    h_pass = (len(df_ind) <= 298)

    # I: 60이평 <= 120이평 <= 224이평 (역배열)
    i_pass = False
    if not np.isnan(r0['MA224']):
        i_pass = (r0['MA60'] <= r0['MA120'] <= r0['MA224'])

    # J: 120이평 <= 60이평 <= 224이평
    j_pass = False
    if not np.isnan(r0['MA224']):
        j_pass = (r0['MA120'] <= r0['MA60'] <= r0['MA224'])

    # K: 60이평 <= 224이평 <= 120이평
    k_pass = False
    if not np.isnan(r0['MA224']):
        k_pass = (r0['MA60'] <= r0['MA224'] <= r0['MA120'])

    # L: (종가 224)이평 하락+보합추세유지 2회 이상
    l_pass = False
    if not np.isnan(r0['MA224']) and not np.isnan(r1['MA224']):
        r2_ma224 = df_ind.iloc[-3]['MA224'] if len(df_ind) >= 3 else np.nan
        if not np.isnan(r2_ma224):
            l_pass = (r0['MA224'] <= r1['MA224']) and (r1['MA224'] <= r2_ma224)

    # M: (종가 448)이평 하락+보합추세유지 2회 이상
    m_pass = False
    if not np.isnan(r0['MA448']) and not np.isnan(r1['MA448']):
        r2_ma448 = df_ind.iloc[-3]['MA448'] if len(df_ind) >= 3 else np.nan
        if not np.isnan(r2_ma448):
            m_pass = (r0['MA448'] <= r1['MA448']) and (r1['MA448'] <= r2_ma448)

    # N: 1봉전 종가<=1봉전 시가, 1봉전 60이평 종가 < 1봉전 종가, 1봉전 20이평 종가 <= 1봉전 13이평 종가 1회이상
    n_pass = False
    for k_idx in range(1, 14):
        if k_idx < len(df_ind):
            rk = df_ind.iloc[-k_idx]
            if (rk['Close'] <= rk['Open']) and (rk['Close'] > rk['MA60']) and (rk['MA20'] <= rk['MA13']):
                n_pass = True
                break

    # 유저 지정 원본 절대 조합식:
    # A and B and !C and D and !E and (F or G) and !H and !I and !J and !K and !L and !M and N
    is_adk_match = (
        a_pass and b_pass and (not c_pass) and d_pass and (not e_pass) and
        (f_pass or g_pass) and (not h_pass) and (not i_pass) and (not j_pass) and
        (not k_pass) and (not l_pass) and (not m_pass) and n_pass
    )

    if is_adk_match:
        # 유저 수칙: 종가/현재가가 13일선 또는 20일선에 2% 이내 초근접한 종목만 채택하여 TOP 1 가산점 부여! (2% 초과 시 스킵)
        disp_ma13 = abs(r0['Close'] - r0['MA13']) / r0['MA13'] if not np.isnan(r0['MA13']) else 0.99
        disp_ma20 = abs(r0['Close'] - r0['MA20']) / r0['MA20'] if not np.isnan(r0['MA20']) else 0.99
        
        is_ultra_close = (disp_ma13 <= 0.02) or (disp_ma20 <= 0.02)
        
        if is_ultra_close:
            hit_ma_str = "13일선" if disp_ma13 <= 0.02 else "20일선"
            min_disp_pct = round(min(disp_ma13, disp_ma20) * 100, 2)
            return {
                "strategy": "ADK특 (양음양 13~20일선 핵심반등)",
                "priority_stage": 0,  # Stage 0: 최우선 TOP 1 승격
                "close": int(r0['Close']),
                "change_rate": round(((r0['Close'] - r1['Close']) / r1['Close']) * 100, 2),
                "amount_100m": round(r0['Amount'] / 100_000_000, 1),
                "reason": f"★ [ADK특 TOP1] 20봉내 400억+ Envelope상한 돌파 후 {hit_ma_str} {min_disp_pct}% 이격 초근접 반등",
                "support_ma": f"{hit_ma_str} ({min_disp_pct}%)",
                "is_adk_top1": True
            }

    return None


def screen_strategy1_yang_eum_yang(df: pd.DataFrame) -> dict:
    """
    전략 1: 양음양 & 사윗감 매매 스크리닝 (Stage 1: ADK특 최우선 ➔ Stage 2: 양음양 일반)
    """
    if df.empty or len(df) < 25:
        return None

    # 0. ADK특 최우선 검증
    res_adk = screen_adk_special(df)
    if res_adk:
        return res_adk

    # 기술적 지표 계산
    df_ind = calculate_technical_indicators(df)
    
    # 전일대비 등락률 계산
    df_ind['Prev_Close'] = df_ind['Close'].shift(1)
    df_ind['Change_Rate'] = (df_ind['Close'] - df_ind['Prev_Close']) / df_ind['Prev_Close'] * 100
    
    latest = df_ind.iloc[-1]
    latest_close = latest['Close']
    
    # 1. 최근 5거래일(오늘 제외) 내 기준봉(500억+등락률 15% 이상 또는 상한가) 존재 여부
    lookback_window = df_ind.iloc[-6:-1]
    if len(lookback_window) < 1:
        return None
        
    has_base = False
    base_row = None
    base_chg_rate = 0.0
    
    for idx, row in lookback_window.iterrows():
        row_amount = row['Amount']
        row_change = row['Change_Rate']
        
        is_row_upper = (row_change >= UPPER_LIMIT_PCT)
        is_row_huge_volume = (row_amount >= STRATEGY1_MIN_AMOUNT) and (row_change >= STRATEGY1_MIN_PCT)
        
        if is_row_upper or is_row_huge_volume:
            has_base = True
            base_row = row
            base_chg_rate = row_change
            break
            
    if not has_base:
        return None

    # 2. 오늘 지지선 (3, 5, 8, 13, 20일선) 근접 확인
    support_mas = [3, 5, 8, 13, 20]
    near_support = False
    hit_ma = None
    hit_disp = None
    
    for ma in support_mas:
        ma_val = latest.get(f'MA_{ma}', np.nan)
        if np.isnan(ma_val):
            continue
        disp = ((latest_close / ma_val) - 1) * 100
        if -3.0 <= disp <= 2.0:
            near_support = True
            hit_ma = ma
            hit_disp = round(disp, 2)
            break
            
    if not near_support:
        return None

    # 사윗감 매칭 검증 (상한가 + 윗꼬리 + 2일차 거래량 감소)
    is_sawitgam = False
    if base_chg_rate >= UPPER_LIMIT_PCT:
        yesterday = df_ind.iloc[-2]
        # 직전일 거래량이 기준봉 거래량 대비 크게 감소했는지 확인
        if yesterday['Volume'] < base_row['Volume'] * 0.7:
            is_sawitgam = True

    return {
        "strategy": "양음양 & 사윗감",
        "close": int(latest_close),
        "change_rate": round(((latest_close - latest['Prev_Close']) / latest['Prev_Close'] * 100), 2),
        "amount_100m": round(latest['Amount'] / 100_000_000, 1),
        "base_date": base_row.name.strftime('%Y-%m-%d') if hasattr(base_row.name, 'strftime') else str(base_row.name),
        "base_detail": f"+{base_chg_rate:.1f}% 장대양봉" if base_chg_rate < UPPER_LIMIT_PCT else "상한가",
        "base_amount": base_row.get("Amount", 0.0),
        "support_ma": f"{hit_ma}일선",
        "disp": hit_disp,
        "reason": f"과거 {base_row.name.strftime('%Y-%m-%d') if hasattr(base_row.name, 'strftime') else str(base_row.name)} 기준봉 후 현재 {hit_ma}일선 지지",
        "sawitgam": is_sawitgam
    }


def screen_kiwoom_iilhong(df: pd.DataFrame) -> dict:
    """
    Stage 1: 키움증권 정석 이일홍 조건검색식 (A~S)
    """
    if df.empty or len(df) < 120:
        return None

    df_ind = calculate_technical_indicators(df)
    df_ind['MA60'] = df_ind['Close'].rolling(60).mean()
    df_ind['MA10'] = df_ind['Close'].rolling(10).mean()

    r0 = df_ind.iloc[-1]
    r1 = df_ind.iloc[-2]
    r2 = df_ind.iloc[-3]

    # A: 40봉 이내 거래대금 50억 이상
    a_pass = (df_ind['Amount'].tail(40).max() >= 5_000_000_000)

    # B: 0봉전 종가가 40봉 중 최고종가 5% 이내 근접
    max_close_40 = df_ind['Close'].tail(40).max()
    b_pass = (r0['Close'] >= max_close_40 * 0.95)

    # C: 60일선 상승+보합
    c_pass = (r0['MA60'] >= r1['MA60'])

    # D: 전일 대비 오늘 종가 5% 이상
    d_pass = ((r0['Close'] - r1['Close']) / r1['Close'] >= 0.05)

    # E: 오늘 시가 대비 종가 5% 이상 (꽉 찬 속양봉)
    e_pass = ((r0['Close'] - r0['Open']) / r0['Open'] >= 0.05)

    # F~J: 최근 5일 중 저가가 10일선 이하 1회 이상 (지지 접지)
    fj_pass = False
    for k in range(1, 6):
        rk = df_ind.iloc[-k]
        if rk['Low'] <= rk['MA10']:
            fj_pass = True
            break

    # K: 거래대금 10억 이상
    k_pass = (r0['Amount'] >= 1_000_000_000)

    # N: 5일선-20일선 10% 이내 수렴
    n_pass = False
    for k in range(1, 3):
        rk = df_ind.iloc[-k]
        if abs(rk['MA_5'] - rk['MA_20']) / rk['MA_20'] <= 0.10:
            n_pass = True
            break

    # O: 20일선-60일선 15% 이내 수렴
    o_pass = False
    for k in range(1, 3):
        rk = df_ind.iloc[-k]
        if abs(rk['MA_20'] - rk['MA60']) / rk['MA60'] <= 0.15:
            o_pass = True
            break

    # P: 오늘 시가가 5일선 0~105% 이하
    p_pass = (r0['Open'] <= r0['MA_5'] * 1.05)

    # Q: 오늘 시가가 60일선 0~105% 이하
    q_pass = (r0['Open'] <= r0['MA60'] * 1.05)

    # !S: 직전 2일간(1~2봉전) +6% 이상 급등 2회 이상 발생 종목 제외 (!S)
    ret_r1 = (r1['Close'] - r2['Close']) / r2['Close']
    r3 = df_ind.iloc[-4]
    ret_r2 = (r2['Close'] - r3['Close']) / r3['Close']
    s_count = (1 if ret_r1 >= 0.06 else 0) + (1 if ret_r2 >= 0.06 else 0)
    s_pass = not (s_count >= 2)

    if a_pass and b_pass and c_pass and d_pass and e_pass and fj_pass and k_pass and n_pass and o_pass and p_pass and q_pass and s_pass:
        return {
            "strategy": "이일홍 정석 (키움 1순위)",
            "priority_stage": 1,
            "close": int(r0['Close']),
            "change_rate": round(((r0['Close'] - r1['Close']) / r1['Close']) * 100, 2),
            "amount_100m": round(r0['Amount'] / 100_000_000, 1),
            "reason": f"★ [1순위 키움정석] 40일 최고가 근접 + 60일선 상승 + 시가대비 +{round(((r0['Close'] - r0['Open'])/r0['Open'])*100, 1)}% 속양봉"
        }

    return None


def screen_strategy2_iilhong(df: pd.DataFrame) -> dict:
    """
    전략 2: 하이브리드 이일홍 스크리닝 (Stage 1: 키움 정석 최우선 ➔ Stage 2: 240일선 접지 폴백)
    """
    if df.empty or len(df) < 120:
        return None

    # 1. Stage 1 (키움 이일홍 정석 최우선 검증)
    res_kiwoom = screen_kiwoom_iilhong(df)
    if res_kiwoom:
        return res_kiwoom

    # 2. Stage 2 (기존 240일선 접지 이일홍 폴백)
    if len(df) < 240:
        return None

    df_ind = calculate_technical_indicators(df)
    df_ind['Vol_MA20'] = df_ind['Volume'].rolling(window=20).mean()
    df_ind['Prev_Close'] = df_ind['Close'].shift(1)
    
    latest = df_ind.iloc[-1]
    latest_close = latest['Close']

    lookback_window = df_ind.iloc[-STRATEGY2_LOOKBACK:-5]
    if len(lookback_window) < 1:
        return None
        
    has_maejib = False
    maejib_date = ""
    maejib_vol = 0.0
    
    for idx, row in lookback_window.iterrows():
        vol_ma = row['Vol_MA20']
        if np.isnan(vol_ma) or vol_ma == 0:
            continue
            
        is_vol_explode = (row['Volume'] >= vol_ma * STRATEGY2_VOLUME_MULT)
        upper_tail = row['High'] - max(row['Open'], row['Close'])
        is_upper_tail = (upper_tail >= row['Close'] * 0.05)
        
        if is_vol_explode and is_upper_tail:
            has_maejib = True
            maejib_date = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)
            maejib_vol = round(row['Volume'] / 100_000, 1)
            break
            
    if not has_maejib:
        return None

    ma20 = latest.get('MA_20', np.nan)
    ma120 = latest.get('MA_120', np.nan)
    ma240 = latest.get('MA_240', np.nan)
    
    if np.isnan(ma20) or np.isnan(ma120) or np.isnan(ma240):
        return None
        
    max_ma = max(ma20, ma120, ma240)
    min_ma = min(ma20, ma120, ma240)
    convergence = (max_ma / min_ma - 1) * 100

    disp_ma240 = ((latest_close / ma240) - 1) * 100
    if not (-3.0 <= disp_ma240 <= 3.0):
        return None

    today_change = round(((latest_close - latest['Prev_Close']) / latest['Prev_Close'] * 100), 2)

    return {
        "strategy": "매집봉 & 이일홍 (2순위 240일선)",
        "priority_stage": 2,
        "close": int(latest_close),
        "change_rate": today_change,
        "amount_100m": round(latest['Amount'] / 100_000_000, 1),
        "maejib_date": maejib_date,
        "maejib_vol": f"{maejib_vol}만 주",
        "convergence": f"{convergence:.2f}%",
        "ma20": round(ma20, 1),
        "ma120": round(ma120, 1),
        "ma240": round(ma240, 1),
        "reason": f"과거 {maejib_date} 매집봉 ➔ 240일선 근접 지지 ({disp_ma240:+.2f}%)"
    }


def screen_strategy3_sugeub_halt(df: pd.DataFrame, kis_investor_list: list) -> dict:
    """
    전략 3: 수급 & 핥 기법 스크리닝
    """
    if df.empty or len(df) < 120 or not kis_investor_list or len(kis_investor_list) < 20:
        return None

    df_ind = calculate_technical_indicators(df)
    latest = df_ind.iloc[-1]
    latest_close = latest['Close']
    
    # 1. 52주 최고가 대비 50% 이하 여부
    high_52w = df_ind['High'].tail(250).max()
    if latest_close > high_52w * (STRATEGY3_BOTTOM_PCT / 100.0):
        return None

    # 2. 최근 20일 외인/기관 순매수 수급 합산 (백만 원 단위 보정)
    df_inv = pd.DataFrame(kis_investor_list)
    df_inv_20 = df_inv.head(20).copy()
    
    df_inv_20['frgn_ntby_tr_pbmn'] = pd.to_numeric(df_inv_20['frgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
    df_inv_20['orgn_ntby_tr_pbmn'] = pd.to_numeric(df_inv_20['orgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
    
    sum_frgn_20 = df_inv_20['frgn_ntby_tr_pbmn'].sum()
    sum_orgn_20 = df_inv_20['orgn_ntby_tr_pbmn'].sum()
    
    has_major_buy = (sum_frgn_20 >= STRATEGY3_MAJOR_BUY) or (sum_orgn_20 >= STRATEGY3_MAJOR_BUY)
    if not has_major_buy:
        return None

    # 3. 최근 5일 기타법인 수급 합산 (추정)
    df_inv_5 = df_inv.head(5).copy()
    df_inv_5['prsn_ntby_tr_pbmn'] = pd.to_numeric(df_inv_5['prsn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
    df_inv_5['frgn_ntby_tr_pbmn'] = pd.to_numeric(df_inv_5['frgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
    df_inv_5['orgn_ntby_tr_pbmn'] = pd.to_numeric(df_inv_5['orgn_ntby_tr_pbmn'], errors='coerce') * 1_000_000
    
    sum_prsn_5 = df_inv_5['prsn_ntby_tr_pbmn'].sum()
    sum_frgn_5 = df_inv_5['frgn_ntby_tr_pbmn'].sum()
    sum_orgn_5 = df_inv_5['orgn_ntby_tr_pbmn'].sum()
    
    etc_net_buy_5 = -(sum_prsn_5 + sum_frgn_5 + sum_orgn_5)
    
    df_inv_5['prsn_ntby_qty'] = pd.to_numeric(df_inv_5['prsn_ntby_qty'], errors='coerce')
    df_inv_5['frgn_ntby_qty'] = pd.to_numeric(df_inv_5['frgn_ntby_qty'], errors='coerce')
    df_inv_5['orgn_ntby_qty'] = pd.to_numeric(df_inv_5['orgn_ntby_qty'], errors='coerce')
    
    sum_prsn_qty_5 = df_inv_5['prsn_ntby_qty'].sum()
    sum_frgn_qty_5 = df_inv_5['frgn_ntby_qty'].sum()
    sum_orgn_qty_5 = df_inv_5['orgn_ntby_qty'].sum()
    
    etc_net_qty_5 = -(sum_prsn_qty_5 + sum_frgn_qty_5 + sum_orgn_qty_5)
    
    has_etc_buy = (etc_net_qty_5 >= STRATEGY3_ETC_CORP_QTY)
    if not has_etc_buy:
        return None

    # 4. 핥기 정보성 탐지 (최근 5거래일 동안 60일선, 120일선, 240일선 근접 흔적 확인 - 미충족되어도 통과)
    recent_5_days = df_ind.tail(5)
    
    hit_ma = "없음"
    hit_disp = 0.0
    hit_date = "N/A"
    
    for ma_period, ma_col in [("60일선", "MA_60"), ("120일선", "MA_120"), ("240일선", "MA_240")]:
        found_touch = False
        for idx, row in recent_5_days.iterrows():
            ma_val = row.get(ma_col, np.nan)
            if np.isnan(ma_val):
                continue
            row_close = row['Close']
            disp = ((row_close / ma_val) - 1) * 100
            
            if -2.0 <= disp <= 1.0:
                hit_ma = ma_period
                latest_ma_val = latest.get(ma_col)
                hit_disp = round(((latest_close / latest_ma_val) - 1) * 100, 2) if not np.isnan(latest_ma_val) else 0.0
                hit_date = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)
                found_touch = True
                break
        if found_touch:
            break

    prev_close = df_ind['Close'].iloc[-2] if len(df_ind) >= 2 else latest_close
    today_change = round(((latest_close - prev_close) / prev_close * 100), 2)

    return {
        "strategy": "수급 & 핥",
        "close": int(latest_close),
        "change_rate": today_change,
        "amount_100m": round(latest['Amount'] / 100_000_000, 1),
        "high_52w": int(high_52w),
        "pct_of_high": round(latest_close / high_52w * 100, 1),
        "frgn_20": round(sum_frgn_20 / 100_000_000, 1),
        "orgn_20": round(sum_orgn_20 / 100_000_000, 1),
        "etc_buy_5": round(etc_net_buy_5 / 100_000_000, 1),
        "etc_qty_5": int(etc_net_qty_5),
        "support_ma": hit_ma,
        "disp": hit_disp,
        "reason": f"52주 대비 바닥권({round(latest_close / high_52w * 100, 1)}%) ➔ 수급 확인 ➔ {hit_date}일 {hit_ma} 핥기 및 반등 포착"
    }


def screen_3or5_ma_settle(df: pd.DataFrame) -> dict:
    """
    신규 스크리너 A: 키움 3일선 또는 5일선 안착 정석 검색식
    공식: (A or B) and (C or D) and E and !G
    - A/B: 최근 3봉 이내 종가가 3일선 또는 5일선 골든크로스
    - C/D: 0봉전 3일선 <= 10일선 또는 5일선 <= 10일선
    - E: 최근 120봉 이내 거래량 500%+ 급증 1회 이상
    - !G: 0봉전 종가 >= 5일선 (5일선 위 안착)
    """
    if df.empty or len(df) < 120:
        return None

    df_ind = calculate_technical_indicators(df)
    df_ind['MA_1'] = df_ind['Close']
    df_ind['MA_3'] = df_ind['Close'].rolling(3).mean()
    df_ind['MA_5'] = df_ind['Close'].rolling(5).mean()
    df_ind['MA_10'] = df_ind['Close'].rolling(10).mean()
    df_ind['Vol_Ratio'] = df_ind['Volume'] / df_ind['Volume'].shift(1) * 100

    latest = df_ind.iloc[-1]
    latest_close = latest['Close']
    prev_close = df_ind['Close'].iloc[-2] if len(df_ind) >= 2 else latest_close

    ma3 = latest.get('MA_3', np.nan)
    ma5 = latest.get('MA_5', np.nan)
    ma10 = latest.get('MA_10', np.nan)

    if np.isnan(ma3) or np.isnan(ma5) or np.isnan(ma10):
        return None

    # A or B: 최근 3봉 이내 골든크로스
    def check_gc(ma_col):
        for i in range(3):
            idx_curr = -1 - i
            idx_prev = idx_curr - 1
            if abs(idx_prev) > len(df_ind):
                continue
            if df_ind['Close'].iloc[idx_prev] < df_ind[ma_col].iloc[idx_prev] and df_ind['Close'].iloc[idx_curr] >= df_ind[ma_col].iloc[idx_curr]:
                return True
        return False

    cond_AB = check_gc('MA_3') or check_gc('MA_5')
    if not cond_AB:
        return None

    # C or D: 0봉전 MA3 <= MA10 또는 MA5 <= MA10
    cond_CD = (ma3 <= ma10) or (ma5 <= ma10)
    if not cond_CD:
        return None

    # E: 120봉 이내 거래량 500%+ 급증 1회 이상
    recent_120 = df_ind.tail(120)
    cond_E = (recent_120['Vol_Ratio'] >= 500.0).any()
    if not cond_E:
        return None

    # !G: 0봉전 종가 >= 5일선 (Close >= MA_5)
    cond_notG = latest_close >= ma5
    if not cond_notG:
        return None

    today_change = round(((latest_close - prev_close) / prev_close * 100), 2)
    disp3 = round(((latest_close / ma3) - 1) * 100, 2)
    disp5 = round(((latest_close / ma5) - 1) * 100, 2)

    return {
        "strategy": "3일선/5일선 안착",
        "close": int(latest_close),
        "change_rate": today_change,
        "amount_100m": round(latest['Amount'] / 100_000_000, 1),
        "disp3": disp3,
        "disp5": disp5,
        "reason": f"키움 A~G 정석 안착 (3일선 {disp3:+.2f}%, 5일선 {disp5:+.2f}% 안착)"
    }


def screen_upper_limit_or_high29(df: pd.DataFrame) -> dict:
    """
    신규 스크리너 B: 지난주(최근 5거래일) 상한가 또는 고가 29%+ 도달 종목
    """
    if df.empty or len(df) < 10:
        return None

    recent_5 = df.tail(5).copy()
    recent_5['Prev_Close'] = recent_5['Close'].shift(1)
    
    if len(df) >= 6:
        recent_5.iloc[0, recent_5.columns.get_loc('Prev_Close')] = df.iloc[-6]['Close']

    has_upper = False
    max_high_pct = 0.0
    hit_date = ""

    for idx, row in recent_5.iterrows():
        p_close = row['Prev_Close']
        if pd.isna(p_close) or p_close == 0:
            continue
        high_pct = ((row['High'] - p_close) / p_close) * 100
        if high_pct >= 29.0:
            has_upper = True
            if high_pct > max_high_pct:
                max_high_pct = high_pct
                hit_date = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)

    if not has_upper:
        return None

    latest = df.iloc[-1]
    latest_close = latest['Close']
    prev_close = df['Close'].iloc[-2] if len(df) >= 2 else latest_close
    today_change = round(((latest_close - prev_close) / prev_close * 100), 2)

    return {
        "strategy": "상한가/고가29%",
        "close": int(latest_close),
        "change_rate": today_change,
        "amount_100m": round(latest['Amount'] / 100_000_000, 1),
        "max_high_pct": round(max_high_pct, 2),
        "hit_date": hit_date,
        "reason": f"최근 {hit_date} 고가 +{max_high_pct:.1f}% 형성 (상한가/급등파동)"
    }

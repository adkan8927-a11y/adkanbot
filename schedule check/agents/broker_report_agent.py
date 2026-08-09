import os
import re
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path

REPORTS_DIR = Path("/Users/adkan/adkan연구2/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CSV_FILE = REPORTS_DIR / "broker_upgrades.csv"

class BrokerReportAgent:
    def __init__(self):
        self.naver_url = "https://finance.naver.com/research/company_list.naver"
        self.wise_url = "https://comp.wisereport.co.kr/earnings/e1020001.aspx?cmp_cd=005930&cn="
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    def _convert_date_format(self, date_str: str) -> str:
        """YYYY-MM-DD -> YY/MM/DD (WiseReport format)"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%y/%m/%d")
        except:
            return ""
            
    def _convert_naver_date(self, date_str: str) -> str:
        """YYYY-MM-DD -> YY.MM.DD (Naver format)"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%y.%m.%d")
        except:
            return ""

    def run_collection(self, target_date_str: str = None):
        """와이즈리포트 상향 데이터 및 네이버 PDF 링크 수집 -> CSV 저장"""
        if not target_date_str:
            target_date_str = datetime.now().strftime("%Y-%m-%d")
            
        wise_date = self._convert_date_format(target_date_str)
        naver_date = self._convert_naver_date(target_date_str)
        
        print(f"📡 [BrokerReportAgent] 데이터 수집 시작 (기준일: {target_date_str})")
        
        # 1. 와이즈리포트 파싱
        wise_data = []
        try:
            res = requests.get(self.wise_url, headers=self.headers, timeout=5)
            # 정규식으로 var changePrc = [...] 내부의 특정 날짜 배열 추출
            pattern = rf'\["{wise_date}".*?\]'
            matches = re.finditer(pattern, res.text)
            
            for match in matches:
                try:
                    row = json.loads(match.group(0))
                    # row: ["26/08/07", "282330|BGF리테일", "박종대", "하나", "172,000", "165,000", "153,100", "4.24"]
                    code_name = row[1].split('|')
                    code = code_name[0]
                    name = code_name[1]
                    broker = row[3]
                    change_rate = float(row[7])
                    
                    if change_rate >= 0.0:  # 상향된 것만 모두 수집 (필터링은 매매판단에서)
                        wise_data.append({
                            "일자": target_date_str,
                            "종목코드": code,
                            "종목명": name,
                            "증권사": broker,
                            "목표가상승률(%)": change_rate,
                            "리포트제목": "",
                            "PDF링크": ""
                        })
                except Exception as e:
                    pass
            print(f"✅ 와이즈리포트 상향 리포트 {len(wise_data)}건 포착")
        except Exception as e:
            print(f"⚠️ 와이즈리포트 크롤링 에러: {e}")

        # 2. 네이버 금융 PDF 링크 수집 (최근 15페이지 넉넉히 스캔)
        naver_reports = {}
        try:
            for page in range(1, 15):
                url = f"{self.naver_url}?&page={page}"
                res = requests.get(url, headers=self.headers, timeout=5)
                res.encoding = "euc-kr"
                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.select_one("table.type_1")
                if not table: continue
                
                for tr in table.select("tr"):
                    cols = tr.select("td")
                    if len(cols) >= 5:
                        stock = cols[0].text.strip()
                        title_tag = cols[1].select_one("a")
                        title = title_tag.text.strip() if title_tag else cols[1].text.strip()
                        broker = cols[2].text.strip()
                        
                        pdf_tag = cols[3].select_one("a")
                        pdf_link = pdf_tag["href"] if pdf_tag and "href" in pdf_tag.attrs else ""
                        
                        date = cols[4].text.strip()
                        if date == naver_date:
                            b_simple = broker.replace("증권", "").replace("투자", "")
                            naver_reports[(stock, b_simple)] = {"title": title, "link": pdf_link}
                            
            print(f"✅ 네이버 금융 리서치 스캔 완료")
        except Exception as e:
            print(f"⚠️ 네이버 리서치 크롤링 에러: {e}")

        # 3. 융합 (Cross-matching)
        for item in wise_data:
            stock = item["종목명"]
            b_simple = item["증권사"].replace("투자", "")
            
            match = naver_reports.get((stock, b_simple))
            if not match:
                # Fallback: 브로커 이름 부분 일치
                for (n_stock, n_broker), data in naver_reports.items():
                    if stock == n_stock and (b_simple in n_broker or n_broker in b_simple):
                        match = data
                        break
            
            if match:
                item["리포트제목"] = match["title"]
                item["PDF링크"] = match["link"]
                
        # 4. CSV 저장 (기존 데이터와 병합하여 누적 저장)
        df_new = pd.DataFrame(wise_data)
        if not df_new.empty:
            df_new = df_new.sort_values(by="목표가상승률(%)", ascending=False)
            if CSV_FILE.exists():
                df_old = pd.read_csv(CSV_FILE)
                # 동일 일자 데이터 삭제 후 덮어쓰기
                df_old = df_old[df_old["일자"] != target_date_str]
                df_final = pd.concat([df_old, df_new], ignore_index=True)
            else:
                df_final = df_new
                
            df_final.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
            print(f"💾 {CSV_FILE} 에 {len(df_new)}건 저장 완료!")
        else:
            print(f"ℹ️ {target_date_str} 기준 목표가 상향 리포트가 없습니다.")


    # ==========================================
    # 📊 대시보드 포맷팅 함수들
    # ==========================================
    
    @staticmethod
    def format_standard_dashboard(target_date_str: str = None) -> str:
        """대시보드쪽 3컬럼 규격: 종목 / 증권사 / 상승률"""
        if not CSV_FILE.exists(): return ""
        df = pd.read_csv(CSV_FILE)
        if df.empty: return ""
        
        target_df = df[df["일자"] == target_date_str] if target_date_str else pd.DataFrame()
        if target_df.empty:
            latest_date = df["일자"].max()
            target_df = df[df["일자"] == latest_date]

        # 1. 제목이 없는 항목 제외 ("제목이 없으면 빼자")
        target_df = target_df[
            target_df['리포트제목'].notna() & 
            (target_df['리포트제목'].astype(str).str.strip() != '') & 
            (target_df['리포트제목'].astype(str).str.strip() != 'nan')
        ]
        if target_df.empty: return ""

        # 2. 동일 종목 내 동일 리포트 제목 중복 제거 (목표가상승률 높은 순 유지)
        target_df = target_df.sort_values(by="목표가상승률(%)", ascending=False).drop_duplicates(subset=['종목명', '리포트제목'], keep='first')
        
        md = "| 종목 | 증권사 | 상승률(%) |\n"
        md += "| :--- | :--- | :---: |\n"
        for _, row in target_df.iterrows():
            md += f"| **{row['종목명']}** | {row['증권사']} | +{row['목표가상승률(%)']:.2f}% |\n"
        return md

    @staticmethod
    def format_global_dashboard(target_date_str: str = None) -> str:
        """글로벌투자대시보드쪽: 종목 / 증권사 / 상승률 / 링크달린제목"""
        if not CSV_FILE.exists(): return ""
        df = pd.read_csv(CSV_FILE)
        if df.empty: return ""
        
        target_df = df[df["일자"] == target_date_str] if target_date_str else pd.DataFrame()
        if target_df.empty:
            latest_date = df["일자"].max()
            target_df = df[df["일자"] == latest_date]

        # 1. 제목이 없는 항목 제외 ("제목이 없으면 빼자")
        target_df = target_df[
            target_df['리포트제목'].notna() & 
            (target_df['리포트제목'].astype(str).str.strip() != '') & 
            (target_df['리포트제목'].astype(str).str.strip() != 'nan')
        ]
        if target_df.empty: return ""

        # 2. 동일 종목 내 동일 리포트 제목 중복 제거 (목표가상승률 높은 순 유지)
        target_df = target_df.sort_values(by="목표가상승률(%)", ascending=False).drop_duplicates(subset=['종목명', '리포트제목'], keep='first')
        
        md = "| 종목 | 증권사 | 상승률(%) | 리포트 |\n"
        md += "| :--- | :--- | :---: | :--- |\n"
        for _, row in target_df.iterrows():
            title = str(row['리포트제목']).strip()
            link = str(row['PDF링크']).strip() if pd.notna(row['PDF링크']) else ""
            if link and link != "nan":
                title_fmt = f"[{title}]({link})"
            else:
                title_fmt = title
                
            md += f"| **{row['종목명']}** | {row['증권사']} | +{row['목표가상승률(%)']:.2f}% | {title_fmt} |\n"
        return md

def get_broker_report_schedules():
    """
    일정 오케스트레이터 연동용 진입점
    데이터만 수집하여 CSV에 저장하며, 반환되는 일정 리스트는 없음(대시보드에서 직접 CSV 렌더링)
    """
    try:
        agent = BrokerReportAgent()
        target = datetime.now().strftime("%Y-%m-%d")
        agent.run_collection(target)
    except Exception as e:
        print(f"⚠️ 목표가 상향 리포트 에이전트 구동 에러: {e}")
    return []

if __name__ == "__main__":
    agent = BrokerReportAgent()
    target = datetime.now().strftime("%Y-%m-%d")
    
    # 임시 테스트용
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        
    agent.run_collection(target)
    
    print("\n[일반 대시보드 미리보기]")
    print(BrokerReportAgent.format_standard_dashboard(target))
    
    print("\n[글로벌투자대시보드 미리보기]")
    print(BrokerReportAgent.format_global_dashboard(target))

import os
import glob
import re

print("🛠️ 6월 ~ 7월 전체 기발행 뉴스 리포트 소급 정제 및 재분류 파이프라인 시작...")

# 1. 확장된 2단계 정밀 핀포인트 섹터 보정 함수
def check_and_adjust_sector_all(title, desc, current_sector):
    title_lower = title.lower()
    desc_lower = (desc or "").lower()
    full_text = title_lower + " " + desc_lower
    
    # [1] 증시 지수/마감시황/폭락
    if any(k in title_lower for k in ["서킷브레이커", "지수 폭락", "마감시황", "증시 마감", "장마감", "증시 폭락"]):
        return "경제 일반"

    # [2] M&A / 주요 공시 (자사주, 밸류업, 유증/무증, 권리락, IPO, 소각)
    ma_terms = ["자사주", "주주환원", "밸류업", "무상증자", "유상증자", "권리락", "자사주 소각", "ipo"]
    if any(k in title_lower for k in ma_terms):
        if not any(k in title_lower for k in ["미국", "연준", "fomc", "달러"]):
            return "M&A / 주요 공시"

    # [3] 코인 / STO (블록체인, RWA, 토큰화, 비트코인, 가상자산)
    crypto_terms = ["비트코인", "가상자산", "토큰증권", "sto", "크립토", "이더리움", "리플", "블록체인", "토큰화", "rwa", "스테이블코인"]
    if any(k in full_text for k in crypto_terms):
        return "코인 / STO"

    # [4] BIO / 의료AI
    bio_terms = ["유전자", "단백질 공학", "바이오", "신약", "임상", "치료제", "fda", "펩타이드", "헬스케어", "질환", "백신", "바이오시밀러"]
    if any(k in full_text for k in bio_terms):
        return "BIO / 의료AI"

    # [5] 부동산 (재건축, 미분양, 아파트, 주담대, 집값, 청약, 준공)
    real_estate_terms = ["부동산", "아파트", "전세", "주담대", "집값", "청약", "미분양", "주택 준공", "재건축"]
    if any(k in full_text for k in real_estate_terms):
        return "부동산"

    # [6] 반도체
    semicon_terms = ["반도체", "hbm", "dram", "d램", "낸드", "삼성전자", "sk하이닉스", "파운드리", "cxmt", "ymtc", "창신메모리", "양쯔메모리", "tsmc", "마이크론"]
    if any(k in title_lower for k in semicon_terms):
        return "반도체"

    # [7] 자동차
    if any(k in full_text for k in ["현대차", "기아", "완성차", "도요타", "마스오토", "모빌리티"]):
        if not any(k in title_lower for k in ["반도체", "hbm"]):
            return "자동차"

    # [8] 이차전지
    if any(k in title_lower for k in ["배터리", "이차전지", "전고체", "양극재", "음극재"]):
        return "이차전지"

    # [9] AI / 로봇
    if any(k in title_lower for k in ["인공지능", "로봇", "휴머노이드", "llm", "chatgpt"]) or re.search(r'(?<![a-z])ai(?![a-z])', title_lower):
        return "AI / 로봇"

    # [10] 전력 / 에너지
    if any(k in title_lower for k in ["원전", "태양광", "풍력", "전력", "변압기", "가스복합화력"]):
        return "전력 / 에너지"

    # [11] 조선 / 해운
    if any(k in title_lower for k in ["조선", "해운", "선박", "유조선", "컨테이너선"]):
        return "조선 / 해운"

    # [12] 국방 / 방산
    if any(k in title_lower for k in ["방산", "k-방산", "미사일", "무기", "잠수함"]):
        if "잠수함" in title_lower and "수주" in title_lower:
            return "조선 / 해운"
        return "국방 / 방산"

    # [13] 우주 / 항공
    if any(k in title_lower for k in ["우주", "위성", "uam", "드론"]):
        if any(exc in title_lower for exc in ["사천", "경남지사", "도지사", "우주항공청", "과기부", "시장"]):
            return "정부정책"
        return "우주 / 항공"

    return current_sector

# 2. 리포트 파일 스캔 및 소급 수정을 통한 재배포
reports = glob.glob("reports/**/*.md", recursive=True) + glob.glob("reports/*.md")

SECTOR_ORDER = [
    "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
    "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
    "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
    "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
]

total_reassigned = 0

for fpath in sorted(set(reports)):
    if "index.html" in fpath or "README" in fpath:
        continue
        
    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    header_lines = []
    sector_data = { s: [] for s in SECTOR_ORDER }
    current_sec = None
    
    for line in lines:
        line_str = line.strip()
        if line_str.startswith("# ") or line_str.startswith("> "):
            header_lines.append(line)
        elif line_str.startswith("### "):
            current_sec = line_str.replace("### ", "").strip()
        elif line_str.startswith("*   [") and current_sec:
            m = re.match(r'\*\s+\[(.*?)\]\((.*?)\)', line_str)
            if m:
                title = m.group(1).replace("\\[", "[").replace("\\]", "]")
                link = m.group(2)
                
                # 정밀 핀포인트 섹터 재평가
                new_sec = check_and_adjust_sector_all(title, "", current_sec)
                if new_sec != current_sec:
                    total_reassigned += 1
                    print(f"🔄 [{os.path.basename(fpath)}] '{title[:30]}...' | [{current_sec}] ➔ [{new_sec}] 보정됨")
                
                if new_sec not in sector_data:
                    sector_data[new_sec] = []
                sector_data[new_sec].append((title, link))

    # 새로 정제된 마크다운 조립
    new_md = []
    new_md.extend(header_lines)
    if header_lines and not header_lines[-1].endswith("\n\n"):
        new_md.append("\n")
        
    for sec in SECTOR_ORDER:
        new_md.append(f"### {sec}\n")
        items = sector_data.get(sec, [])
        if not items:
            new_md.append("--------\n\n")
        else:
            seen_titles = set()
            count = 0
            for title, link in items:
                clean_title = title.strip()
                if clean_title in seen_titles:
                    continue
                seen_titles.add(clean_title)
                
                title_escaped = title.replace("[", "\\[").replace("]", "\\]")
                new_md.append(f"*   [{title_escaped}]({link})\n")
                count += 1
            if count == 0:
                new_md.pop()
                new_md.append("--------\n")
            new_md.append("\n")
            
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(new_md)

print(f"\n✨ 소급 재정제 완료: 총 {total_reassigned}건의 오분류 기사가 올바른 섹터로 이동되었습니다!")

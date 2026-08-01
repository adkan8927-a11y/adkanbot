import os
import re

print("⚡ 7월 31일 리포트 수정본 생성 및 전후 차이점 보고서 생성 시작...")

# 26개 전 섹터 핀포인트 보정 매트릭스 (로컬 파이썬 100% 빠른 평가)
def adjust_sector_fast(title, desc, current_sector):
    title_lower = title.lower()
    full_text = title_lower + " " + (desc or "").lower()
    
    # 0. 증시 지수/마감시황
    if any(k in title_lower for k in ["서킷브레이커", "지수 폭락", "마감시황", "증시 마감", "장마감", "증시 폭락"]):
        return "경제 일반"

    # 1. M&A / 주요 공시 (자사주, 밸류업, 유증/무증, 권리락, IPO, 소각)
    ma_terms = ["자사주", "주주환원", "밸류업", "무상증자", "유상증자", "권리락", "자사주 소각", "ipo", "지분 매수", "경영권"]
    if any(k in title_lower for k in ma_terms):
        if not any(k in title_lower for k in ["미국", "연준", "fomc", "달러"]):
            return "M&A / 주요 공시"

    # 2. 코인 / STO
    crypto_terms = ["비트코인", "가상자산", "토큰증권", "sto", "크립토", "이더리움", "리플", "블록체인", "토큰화", "rwa", "스테이블코인", "웹3"]
    if any(k in full_text for k in crypto_terms):
        return "코인 / STO"

    # 3. BIO / 의료AI
    bio_terms = ["유전자", "단백질 공학", "바이오", "신약", "임상", "치료제", "fda", "펩타이드", "헬스케어", "질환", "백신", "바이오시밀러", "의료ai"]
    if any(k in full_text for k in bio_terms):
        return "BIO / 의료AI"

    # 4. 부동산
    real_estate_terms = ["부동산", "아파트", "전세", "주담대", "집값", "청약", "미분양", "주택 준공", "재건축", "도시정비"]
    if any(k in full_text for k in real_estate_terms):
        return "부동산"

    # 5. 반도체
    semicon_terms = ["반도체", "hbm", "dram", "d램", "낸드", "삼성전자", "sk하이닉스", "파운드리", "cxmt", "ymtc", "창신메모리", "양쯔메모리", "tsmc", "마이크론", "socamm", "유리기판"]
    if any(k in title_lower for k in semicon_terms):
        return "반도체"

    # 6. 자동차
    if any(k in full_text for k in ["현대차", "기아", "완성차", "도요타", "마스오토", "모빌리티", "자율주행"]):
        if not any(k in title_lower for k in ["반도체", "hbm"]):
            return "자동차"

    # 7. 이차전지
    if any(k in title_lower for k in ["배터리", "이차전지", "전고체", "양극재", "음극재", "lg에너지솔루션", "sk온", "삼성sdi", "lfp"]):
        return "이차전지"

    # 8. AI / 로봇
    if any(k in title_lower for k in ["인공지능", "로봇", "휴머노이드", "llm", "chatgpt", "생성형 ai", "에이전틱 ai"]) or re.search(r'(?<![a-z])ai(?![a-z])', title_lower):
        return "AI / 로봇"

    # 9. 전력 / 에너지
    if any(k in title_lower for k in ["원전", "smr", "태양광", "풍력", "전력망", "변압기", "가스복합화력"]):
        return "전력 / 에너지"

    # 10. 조선 / 해운
    if any(k in title_lower for k in ["조선", "해운", "선박", "유조선", "컨테이너선", "lng선"]):
        return "조선 / 해운"

    # 11. 국방 / 방산
    if any(k in title_lower for k in ["방산", "k-방산", "미사일", "무기", "잠수함", "방사청", "kddx"]):
        if "잠수함" in title_lower and "수주" in title_lower:
            return "조선 / 해운"
        return "국방 / 방산"

    # 12. 우주 / 항공
    if any(k in title_lower for k in ["우주", "위성", "uam", "드론", "스페이스x"]):
        if any(exc in title_lower for exc in ["사천", "경남지사", "도지사", "우주항공청", "과기부", "시장"]):
            return "정부정책"
        return "우주 / 항공"

    # 13. 정부정책
    if any(k in title_lower for k in ["기재부", "과기부", "식약처", "산업부", "지자체", "정부 정책", "한일포럼"]):
        return "정부정책"

    # 14. 정치
    if any(k in title_lower for k in ["민주당", "국민의힘", "최고위원", "정치권", "여당", "야당"]):
        return "정치"

    # 15. 미중패권전쟁
    if any(k in title_lower for k in ["미중", "고율관세", "대중 제재", "수출 통제", "트럼프 관세"]):
        return "미중패권전쟁"

    # 16. IT / 신기술
    if any(k in title_lower for k in ["알뜰폰", "양자", "사이버보안", "oled", "디스플레이", "핀테크"]):
        return "IT / 신기술"

    return current_sector

SECTOR_ORDER = [
    "경제 일반", "부동산", "미중패권전쟁", "국제 - 미국", "국제 - 유럽", "국제 - 중국", "국제 - 그외", "원자재", "정부정책",
    "반도체", "자동차", "이차전지", "전력 / 에너지", "AI / 로봇", "IT / 신기술",
    "BIO / 의료AI", "조선 / 해운", "우주 / 항공", "코인 / STO", "IP / 엔터",
    "건설 / 인프라", "국방 / 방산", "정치", "M&A / 주요 공시", "해외 이슈", "기타"
]

def reprocess_and_generate(input_file, output_file, is_jh=True):
    if not os.path.exists(input_file):
        print(f"❌ 파일 없음: {input_file}")
        return {}, []

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    sector_data = { s: [] for s in SECTOR_ORDER }
    reassigned_logs = []
    current_sec = None

    for line in lines:
        line_str = line.strip()
        if line_str.startswith("### "):
            current_sec = line_str.replace("### ", "").strip()
        elif line_str.startswith("*   [") and current_sec:
            m = re.match(r'\*\s+\[(.*?)\]\((.*?)\)', line_str)
            if m:
                title = m.group(1).replace("\\[", "[").replace("\\]", "]")
                link = m.group(2)
                
                new_sec = adjust_sector_fast(title, "", current_sec)
                if new_sec != current_sec:
                    reassigned_logs.append({
                        "title": title,
                        "orig": current_sec,
                        "new": new_sec
                    })
                
                if new_sec not in sector_data:
                    sector_data[new_sec] = []
                sector_data[new_sec].append((title, link))

    new_md = []
    if is_jh:
        new_md.append("# 금일 부각된 뉴스 (장후_수정)\n> 수집 시간: 2026-07-31 00:00 ~ 2026-07-31 23:59\n\n")
    else:
        new_md.append("# 장전 주요 뉴스 브리핑 (장전_수정)\n> 수집 시간: 2026-07-30 18:00 ~ 2026-07-31 08:30\n\n")

    for sec in SECTOR_ORDER:
        new_md.append(f"### {sec}\n")
        items = sector_data.get(sec, [])
        if not items:
            new_md.append("--------\n\n")
        else:
            seen = set()
            count = 0
            for title, link in items:
                if title in seen: continue
                seen.add(title)
                t_esc = title.replace("[", "\\[").replace("]", "\\]")
                new_md.append(f"*   [{t_esc}]({link})\n")
                count += 1
            if count == 0:
                new_md.pop()
                new_md.append("--------\n")
            new_md.append("\n")

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(new_md)

    print(f"✅ 수정 리포트 생성 완료: {output_file}")
    return sector_data, reassigned_logs

data_jh, logs_jh = reprocess_and_generate("reports/2026-07-31_장후.md", "reports/2026-07-31_장후_수정.md", is_jh=True)
data_jj, logs_jj = reprocess_and_generate("reports/2026-07-31_장전.md", "reports/2026-07-31_장전_수정.md", is_jh=False)

print(f"📊 장후 보정 기사: {len(logs_jh)}건 | 장전 보정 기사: {len(logs_jj)}건")

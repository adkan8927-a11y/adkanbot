import os
import re
import json
import requests

# 로컬 Ollama 연동 설정
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:e4b"

def extract_schedule_from_text(sector_name, text):
    prompt = f"""너는 경제 및 산업 뉴스 텍스트에서 구체적인 '일정' 정보만 정확하게 추출하는 정밀 분석기이다.
아래의 [텍스트]를 읽고, 언급된 미래의 주요 일정(날짜와 관련 이벤트)을 찾아서 추출해라.

[출력 조건]
1. 오직 "* [월]월 [일]일 [일정 내용]" 포맷의 목록 형태로만 출력해라.
2. 예시: "* 9월 26일 금융노조 총파업"
3. 텍스트에 구체적인 미래의 행사일, 경제 지표 발표일, 소송일, 시행일, 출시일 등 날짜 기반의 일정 정보가 전혀 없거나 불명확하다면 아무것도 출력하지 마라 (빈 응답 반환).
4. 부가적인 부연설명이나 인사말, 서론은 절대 적지 마라.

[텍스트]
{text}
"""
    
    headers = {"Content-Type": "application/json"}
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that extracts schedules in clean Korean format."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(OLLAMA_URL, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            return content
        else:
            print(f"❌ Ollama 호출 실패 (상태 코드: {response.status_code})")
            return ""
    except Exception as e:
        print(f"❌ Ollama 연동 에러: {e}")
        return ""

def main():
    note_path = "/Users/adkan/adkan연구2/작업용/upnote file/new/019e2669-bd13-7278-abb2-1d71583089bf.md"
    if not os.path.exists(note_path):
        print(f"❌ 파일을 찾을 수 없습니다: {note_path}")
        return
        
    with open(note_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # 1. 파일 최상단 날짜 파싱 (# 2023.09.19(화) -> 2023.09.19)
    first_line = lines[0].strip()
    date_match = re.search(r'#\s*([\d\.]+)', first_line)
    if date_match:
        file_date = date_match.group(1).strip()
    else:
        file_date = "unknown_date"
        
    print(f"📅 파싱된 노트 기준 날짜: {file_date}")
    
    # 2. 섹션별 본문 파싱
    content_str = "".join(lines)
    # **< 섹터명 >** 정규식 매칭
    sector_pattern = r'\*\*<\s*([^>]+?)\s*>\*\*'
    
    splits = re.split(sector_pattern, content_str)
    
    # split 결과: [서론, 섹터1, 본문1, 섹터2, 본문2, ...]
    parsed_sections = {}
    if len(splits) > 1:
        # 첫 번째 원소는 헤더 날짜 등이므로 제외
        for i in range(1, len(splits), 2):
            sector_name = splits[i].strip()
            sector_content = splits[i+1].strip() if i+1 < len(splits) else ""
            # nomad: 주석 등 불필요한 라인들은 컨텍스트 축소를 위해 필터링하거나 최소화해서 넣어줍니다.
            parsed_sections[sector_name] = sector_content

    # 3. 각 섹터별 로컬 LLM 호출 및 일정 추출
    extracted_results = []
    
    print(f"🧠 로컬 LLM ({MODEL_NAME})을 사용하여 일정 추출을 진행합니다...")
    for sector, content in parsed_sections.items():
        if not content:
            continue
            
        print(f"⏳ '{sector}' 섹터 분석 중...")
        extracted = extract_schedule_from_text(sector, content)
        
        # 빈칸이 아니거나 가짜 포맷이 아니면 추가
        if extracted and "*" in extracted:
            extracted_results.append(f"### < {sector} >\n{extracted}\n")
        else:
            extracted_results.append(f"### < {sector} >\n*(일정 없음)*\n")

    # 4. 최종 마크다운 보고서로 조립 및 저장
    output_lines = [
        f"요청하신 대로 제공된 텍스트에서 각 섹터명(`< >`) 바로 아래에 있는 주요일정 내용만 추출하여 정리해 드립니다.\n",
    ]
    output_lines.extend(extracted_results)
    
    # 결과 파일 저장
    output_dir = "/Users/adkan/adkan연구2/schedule check"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{file_date}.md")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines).strip() + "\n")
        
    print(f"💾 일정 추출 완료 및 저장 성공: '{output_path}'")

if __name__ == "__main__":
    main()

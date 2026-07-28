import OpenDartReader
import re
api_key = '63cfc7d9c10a4c87a2e735d31f8ff4c4351207de'
dart = OpenDartReader(api_key)
doc = dart.document('20250625000504')
clean_text = re.sub(r'<[^>]+>', '\n', doc)
lines = [l.strip() for l in clean_text.split('\n') if l.strip()]

def find_exact_cb_date(lines):
    for i, line in enumerate(lines):
        if '전환청구기간' in line:
            # 보통 다음 1~5줄 안에 '시작일'과 날짜가 나옴
            for j in range(1, 6):
                if i+j < len(lines):
                    date_match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', lines[i+j])
                    if date_match:
                        # 첫 번째로 나오는 날짜가 시작일임
                        return f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
    return None

print("Exact Start Date:", find_exact_cb_date(lines))

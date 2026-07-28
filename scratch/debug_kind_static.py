import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://kind.krx.co.kr/disclosure/todaydisclosure.do'
}

r = requests.get('https://kind.krx.co.kr/disclosure/todaydisclosure.do?method=searchTodayDisclosureMain&marketType=0', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print("--- 1. Hidden Inputs 목록 ---")
hidden_inputs = soup.find_all('input', type='hidden')
for inp in hidden_inputs:
    print(f"  Name: {inp.get('name')}, Value: {inp.get('value')}")

print("\n--- 2. Form 정보 ---")
forms = soup.find_all('form')
for i, form in enumerate(forms):
    print(f"  Form[{i}] Name: {form.get('name')}, Action: {form.get('action')}, Method: {form.get('method')}")

print("\n--- 3. 날짜 탭 링크 및 속성 ---")
# '06.26'이 포함된 a 태그나 li 태그 분석
a_tags = soup.find_all('a')
for a in a_tags:
    text = a.get_text().strip()
    if '06.' in text or '07.' in text or '05.' in text:
        print(f"  Text: {text} | Href: {a.get('href')} | Onclick: {a.get('onclick')}")

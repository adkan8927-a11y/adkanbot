import requests

url = "https://www.ksd.or.kr/ko/api/board/PRRS"
headers = {"User-Agent": "Mozilla/5.0"}
params = {
    "page": 1,
    "size": 10,
    "searchType": "TITLE",
    "searchWord": "의무보유"
}
try:
    res = requests.get(url, params=params, headers=headers)
    print("Status:", res.status_code)
    print(res.text[:500])
except Exception as e:
    print(e)

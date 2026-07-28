import requests
import json
import os

bgn_de = "20250701"
end_de = "20250731"
DART_API_KEY = os.environ.get("DART_API_KEY", "b30349ed562eef6eb814d44af505f1fbebaee71c")
url = "https://opendart.fss.or.kr/api/list.json"
params = {'crtfc_key': DART_API_KEY, 'bgn_de': bgn_de, 'end_de': end_de, 'page_count': '100', 'corp_cls': 'Y'}

res = requests.get(url, params=params)
data = res.json()
print("Status:", data.get('status'))
print("Message:", data.get('message'))
if 'list' in data:
    print("Total records (Y):", len(data['list']))
    sample = [x['report_nm'] for x in data['list'][:20]]
    print("Sample reports:", sample)
    
params['corp_cls'] = 'K'
res2 = requests.get(url, params=params)
data2 = res2.json()
print("Status (K):", data2.get('status'))
if 'list' in data2:
    print("Total records (K):", len(data2['list']))

import requests
ASSEMBLY_API_KEY = "3a2f7c8d9e1b4a5f8b2c4e6d9f0a1b2c"
url = "https://open.assembly.go.kr/portal/openapi/nekcaiymtcbxspvtd"
params = {
    'KEY': ASSEMBLY_API_KEY,
    'Type': 'json',
    'pIndex': '1',
    'pSize': '10'
}
res = requests.get(url, params=params)
print(res.text[:500])

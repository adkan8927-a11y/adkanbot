import requests
DAPA_API_KEY = "5d5e6d63fb73bc35c5e8e727ebd98ad01c1fd87293666e86a1f0676d35b6c7b6"
url = "https://apis.data.go.kr/1690000/CntrctInfoService/getDmstcCntrctInfoList"
params = {
    'serviceKey': DAPA_API_KEY,
    'pageNo': '1',
    'numOfRows': '5',
    'resultType': 'xml'
}
res = requests.get(url, params=params)
print(res.text)

import OpenDartReader

dart = OpenDartReader("63cfc7d9c10a4c87a2e735d31f8ff4c4351207de")
# 'Y' 코스피, 'K' 코스닥 
df = dart.list(start='20250615', end='20250715', kind='C') # kind='C' is 기업공시
if df is not None:
    cb_reports = df[df['report_nm'].str.contains('전환사채|신주인수권')]
    print(cb_reports[['corp_name', 'report_nm', 'rcept_dt']])
    print("Total found:", len(cb_reports))

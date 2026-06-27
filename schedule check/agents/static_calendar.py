def get_static_schedules():
    static_events = [
        # 글로벌 메이저 학회 및 IT 박람회
        {"date": "2026-06-16", "category": "해외학회/전시", "event": "BIO USA 2026 본행사 (바이오 인터내셔널)", "source": "정적 캘린더"},
        {"date": "2026-08-25", "category": "해외학회/전시", "event": "Gamescom 2026 (유럽 최대 게임쇼 개최)", "source": "정적 캘린더"},
        {"date": "2026-09-04", "category": "해외학회/전시", "event": "IFA 2026 유럽 가전전시회 개최 (~09-09)", "source": "정적 캘린더"},
        {"date": "2026-09-11", "category": "해외학회/전시", "event": "ESMO 2026 유럽종양내과학회 본행사 (~09-15)", "source": "정적 캘린더"},
        {"date": "2026-11-06", "category": "해외학회/전시", "event": "SITC 2026 면역항암학회 본행사 (~11-08)", "source": "정적 캘린더"},
        {"date": "2026-11-29", "category": "해외학회/전시", "event": "RSNA 2026 북미방사선학회 (의료AI 중심) (~12-03)", "source": "정적 캘린더"},
        {"date": "2026-12-05", "category": "해외학회/전시", "event": "ASH 2026 미국혈액학회 본행사 (~12-08)", "source": "정적 캘린더"},
        {"date": "2027-01-06", "category": "해외학회/전시", "event": "CES 2027 세계최대 가전/IT 전시회 (~01-09)", "source": "정적 캘린더"},
        {"date": "2027-01-11", "category": "해외학회/전시", "event": "JP모건 헬스케어 컨퍼런스 2027 (~01-14)", "source": "정적 캘린더"},

        # 2026년 하반기 핵심 미국 거시 경제 일정 (FOMC, CPI)
        {"date": "2026-07-29", "category": "국제 - 미국", "event": "미국 FOMC 금리결정 발표 ★", "source": "정적 캘린더"},
        {"date": "2026-08-12", "category": "국제 - 미국", "event": "미국 7월 소비자물가지수 (CPI) 발표", "source": "정적 캘린더"},
        {"date": "2026-09-16", "category": "국제 - 미국", "event": "미국 FOMC 금리결정 및 분기 전망 점도표 발표 ★★", "source": "정적 캘린더"},
        {"date": "2026-09-16", "category": "국제 - 미국", "event": "미국 8월 소비자물가지수 (CPI) 발표", "source": "정적 캘린더"},
        {"date": "2026-10-14", "category": "국제 - 미국", "event": "미국 9월 소비자물가지수 (CPI) 발표", "source": "정적 캘린더"},
        {"date": "2026-10-28", "category": "국제 - 미국", "event": "미국 FOMC 금리결정 발표 ★", "source": "정적 캘린더"},
        {"date": "2026-11-12", "category": "국제 - 미국", "event": "미국 10월 소비자물가지수 (CPI) 발표", "source": "정적 캘린더"},
        {"date": "2026-12-11", "category": "국제 - 미국", "event": "미국 11월 소비자물가지수 (CPI) 발표", "source": "정적 캘린더"},
        {"date": "2026-12-16", "category": "국제 - 미국", "event": "미국 FOMC 금리결정 발표 ★", "source": "정적 캘린더"}
    ]
    return static_events

if __name__ == "__main__":
    print(get_static_schedules())

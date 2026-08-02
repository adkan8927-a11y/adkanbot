"""
텔레그램 알림 모듈 (telegram_bot.py)
조건 포착 종목 및 차트 이미지를 텔레그램으로 자동 전송 (타임아웃 및 재시도 보정)
"""

import requests
import os
import time
import logging
import socket
from pathlib import Path
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 글로벌 5.0초 소켓 타임아웃 패치
socket.setdefaulttimeout(5.0)

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        if not self.chat_id and self.token:
            self.chat_id = self.auto_detect_chat_id()

    def auto_detect_chat_id(self) -> str:
        """
        봇에 도착한 최근 메시지에서 chat_id를 자동 감지
        """
        try:
            url = f"{self.base_url}/getUpdates"
            res = requests.get(url, timeout=5).json()
            if res.get("ok") and res.get("result"):
                chat_id = str(res["result"][-1]["message"]["chat"]["id"])
                logger.info(f"✅ 텔레그램 Chat ID 자동 감지 완료: {chat_id}")
                return chat_id
        except Exception as e:
            logger.warning(f"텔레그램 Chat ID 자동 감지 실패: {e}")
        return ""

    def send_message(self, text: str, retries: int = 3) -> bool:
        """
        텍스트 메시지 전송 (타임아웃 발생 시 자동 재시도)
        """
        if not self.token or not self.chat_id:
            logger.warning("텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        for attempt in range(1, retries + 1):
            try:
                res = requests.post(url, json=payload, timeout=10)
                if res.json().get("ok", False):
                    return True
            except Exception as e:
                logger.warning(f"텔레그램 메시지 전송 시도 {attempt}/{retries} 실패: {e}")
                time.sleep(1)
        return False

    def send_photo(self, photo_path: str, caption: str = "", retries: int = 3) -> bool:
        """
        이미지 파일(차트 PNG) 및 캡션 전송 (타임아웃 발생 시 자동 재시도 및 폴백)
        """
        if not self.token or not self.chat_id:
            logger.warning("텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
            return False

        if not os.path.exists(photo_path):
            logger.error(f"전송할 이미지 파일이 존재하지 않습니다: {photo_path}")
            return False

        url = f"{self.base_url}/sendPhoto"

        for attempt in range(1, retries + 1):
            try:
                with open(photo_path, "rb") as photo_file:
                    files = {"photo": photo_file}
                    data = {
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "parse_mode": "HTML"
                    }
                    res = requests.post(url, data=data, files=files, timeout=20)
                    if res.json().get("ok", False):
                        return True
            except Exception as e:
                logger.warning(f"텔레그램 이미지 전송 시도 {attempt}/{retries} 실패: {e}")
                time.sleep(2)

        # 이미지 전송 최종 실패 시 텍스트 캡션이라도 폴백 전송
        if caption:
            logger.info("📱 이미지 전송 실패로 텍스트 캡션 폴백 전송을 시도합니다.")
            return self.send_message(caption)
        return False


if __name__ == "__main__":
    bot = TelegramBot()
    if bot.chat_id:
        print(f"Detected Chat ID: {bot.chat_id}")
        bot.send_message("🤖 [연구3] 텔레그램 알림 모듈 테스트 성공!")
    else:
        print("Chat ID를 감지하려면 텔레그램 봇에게 메시지를 보낸 후 다시 실행하세요.")

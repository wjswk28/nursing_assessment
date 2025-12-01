import requests
from flask import current_app

def send_nateon_message(content: str):
    webhook_url = current_app.config.get("NATEON_WEBHOOK_URL")
    if not webhook_url:
        return  # 설정 안 돼 있으면 그냥 종료

    try:
        requests.post(
            webhook_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"content": content},
            timeout=5,
        )
    except Exception as e:
        current_app.logger.error(f"[NATEON ERROR] {e}")

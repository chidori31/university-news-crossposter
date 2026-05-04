import httpx

from app.config import settings


class TelegramClient:
    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_text(self, text: str, parse_mode: str | None = None) -> dict:
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")

        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is not set")

        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
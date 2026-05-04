import httpx

from app.config import settings


class MaxClient:
    def __init__(self) -> None:
        self.bot_token = settings.max_bot_token
        self.chat_id = settings.max_chat_id
        self.base_url = "https://platform-api.max.ru"

    async def send_text(self, text: str, text_format: str | None = None) -> dict:
        if not self.bot_token:
            raise ValueError("MAX_BOT_TOKEN is not set")

        if not self.chat_id:
            raise ValueError("MAX_CHAT_ID is not set")

        url = f"{self.base_url}/messages"

        headers = {
            "Authorization": self.bot_token,
            "Content-Type": "application/json",
        }

        params = {
            "chat_id": self.chat_id,
        }

        payload = {
            "text": text,
        }

        if text_format:
            payload["format"] = text_format

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers=headers,
                params=params,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"MAX API error {response.status_code}: {response.text}"
            )

        return response.json()
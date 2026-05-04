import json

import httpx

from app.config import settings


TELEGRAM_CAPTION_LIMIT = 1024


class TelegramClient:
    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def _validate_settings(self) -> None:
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")

        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is not set")

    async def send_text(self, text: str, parse_mode: str | None = None) -> dict:
        self._validate_settings()

        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_photo(
        self,
        media: dict,
        caption: str | None = None,
    ) -> dict:
        self._validate_settings()

        url = f"{self.base_url}/sendPhoto"

        data = {
            "chat_id": self.chat_id,
        }

        if caption:
            data["caption"] = caption

        files = {
            "photo": (
                media["filename"],
                media["data"],
                media["content_type"],
            )
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()

    async def send_video(
        self,
        media: dict,
        caption: str | None = None,
    ) -> dict:
        self._validate_settings()

        url = f"{self.base_url}/sendVideo"

        data = {
            "chat_id": self.chat_id,
        }

        if caption:
            data["caption"] = caption

        files = {
            "video": (
                media["filename"],
                media["data"],
                media["content_type"],
            )
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()

    async def send_media_group(
        self,
        media_files: list[dict],
        caption: str | None = None,
    ) -> dict:
        self._validate_settings()

        url = f"{self.base_url}/sendMediaGroup"

        media_payload = []
        files = {}

        for index, media in enumerate(media_files):
            file_key = f"media{index}"

            if media["kind"] == "image":
                media_type = "photo"
            elif media["kind"] == "video":
                media_type = "video"
            else:
                raise ValueError(f"Unsupported Telegram media type: {media['content_type']}")

            item = {
                "type": media_type,
                "media": f"attach://{file_key}",
            }

            if index == 0 and caption:
                item["caption"] = caption

            media_payload.append(item)

            files[file_key] = (
                media["filename"],
                media["data"],
                media["content_type"],
            )

        data = {
            "chat_id": self.chat_id,
            "media": json.dumps(media_payload, ensure_ascii=False),
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()

    async def send_post(self, text: str, media_files: list[dict]) -> None:
        if not media_files:
            await self.send_text(text)
            return

        caption = text if len(text) <= TELEGRAM_CAPTION_LIMIT else None

        if len(media_files) == 1:
            media = media_files[0]

            if caption is None:
                await self.send_text(text)

            if media["kind"] == "image":
                await self.send_photo(media, caption=caption)
                return

            if media["kind"] == "video":
                await self.send_video(media, caption=caption)
                return

            raise ValueError(f"Unsupported Telegram media type: {media['content_type']}")

        if caption is None:
            await self.send_text(text)

        await self.send_media_group(media_files, caption=caption)
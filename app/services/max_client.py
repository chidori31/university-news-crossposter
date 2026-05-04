import httpx

from app.config import settings


class MaxClient:
    def __init__(self) -> None:
        self.bot_token = settings.max_bot_token
        self.chat_id = settings.max_chat_id
        self.base_url = "https://platform-api.max.ru"

    def _validate_settings(self) -> None:
        if not self.bot_token:
            raise ValueError("MAX_BOT_TOKEN is not set")

        if not self.chat_id:
            raise ValueError("MAX_CHAT_ID is not set")

    def _headers(self) -> dict:
        return {
            "Authorization": self.bot_token,
            "Content-Type": "application/json",
        }

    async def send_text(self, text: str, text_format: str | None = None) -> dict:
        return await self.send_post(text=text, media_files=[], text_format=text_format)

    async def _upload_media(self, media: dict) -> dict:
        self._validate_settings()

        if media["kind"] == "image":
            upload_type = "image"
        elif media["kind"] == "video":
            upload_type = "video"
        else:
            upload_type = "file"

        upload_init_url = f"{self.base_url}/uploads"

        async with httpx.AsyncClient(timeout=90) as client:
            init_response = await client.post(
                upload_init_url,
                headers={"Authorization": self.bot_token},
                params={"type": upload_type},
            )

            init_response.raise_for_status()
            init_data = init_response.json()

            upload_url = init_data["url"]

            upload_response = await client.post(
                upload_url,
                files={
                    "data": (
                        media["filename"],
                        media["data"],
                        media["content_type"],
                    )
                },
            )

            upload_response.raise_for_status()
            uploaded_data = upload_response.json()

        if media["kind"] == "video" and "token" in init_data:
            payload = {
                "token": init_data["token"],
            }
            payload.update(uploaded_data)
        else:
            payload = uploaded_data

        return {
            "type": upload_type,
            "payload": payload,
        }

    async def send_post(
        self,
        text: str,
        media_files: list[dict],
        text_format: str | None = None,
    ) -> dict:
        self._validate_settings()

        url = f"{self.base_url}/messages"

        params = {
            "chat_id": self.chat_id,
        }

        attachments = []

        for media in media_files:
            attachment = await self._upload_media(media)
            attachments.append(attachment)

        payload = {
            "text": text,
        }

        if attachments:
            payload["attachments"] = attachments

        if text_format:
            payload["format"] = text_format

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                params=params,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"MAX API error {response.status_code}: {response.text}"
            )

        return response.json()
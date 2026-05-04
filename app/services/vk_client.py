import httpx

from app.config import settings


class VkClient:
    def __init__(self) -> None:
        self.access_token = settings.vk_access_token
        self.group_id = settings.vk_group_id
        self.api_version = settings.vk_api_version
        self.base_url = "https://api.vk.com/method"

    def _validate_settings(self) -> None:
        if not self.access_token:
            raise ValueError("VK_ACCESS_TOKEN is not set")

        if not self.group_id:
            raise ValueError("VK_GROUP_ID is not set")

    async def _call_method(self, method: str, payload: dict) -> dict:
        self._validate_settings()

        url = f"{self.base_url}/{method}"

        payload = {
            **payload,
            "access_token": self.access_token,
            "v": self.api_version,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, data=payload)

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"VK API error {error.get('error_code')}: {error.get('error_msg')}"
            )

        return data["response"]

    async def send_text(self, text: str) -> dict:
        payload = {
            "owner_id": f"-{self.group_id}",
            "from_group": 1,
            "message": text,
        }

        return await self._call_method("wall.post", payload)

    async def _upload_wall_photo(
        self,
        photo_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        upload_server = await self._call_method(
            "photos.getWallUploadServer",
            {
                "group_id": self.group_id,
            }
        )

        upload_url = upload_server["upload_url"]

        files = {
            "photo": (filename, photo_bytes, content_type),
        }

        async with httpx.AsyncClient(timeout=60) as client:
            upload_response = await client.post(upload_url, files=files)

        upload_response.raise_for_status()
        uploaded_data = upload_response.json()

        saved_photos = await self._call_method(
            "photos.saveWallPhoto",
            {
                "group_id": self.group_id,
                "photo": uploaded_data["photo"],
                "server": uploaded_data["server"],
                "hash": uploaded_data["hash"],
            }
        )

        saved_photo = saved_photos[0]

        return f"photo{saved_photo['owner_id']}_{saved_photo['id']}"

    async def send_text_with_photos(
        self,
        text: str,
        photos: list[dict],
    ) -> dict:
        attachments = []

        for photo in photos:
            attachment = await self._upload_wall_photo(
                photo_bytes=photo["data"],
                filename=photo["filename"],
                content_type=photo["content_type"],
            )
            attachments.append(attachment)

        payload = {
            "owner_id": f"-{self.group_id}",
            "from_group": 1,
            "message": text,
            "attachments": ",".join(attachments),
        }

        return await self._call_method("wall.post", payload)
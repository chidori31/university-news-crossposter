import httpx

from app.config import settings


class VkClient:
    def __init__(self) -> None:
        self.access_token = settings.vk_access_token
        self.group_id = settings.vk_group_id
        self.api_version = settings.vk_api_version
        self.base_url = "https://api.vk.com/method"

    async def send_text(self, text: str) -> dict:
        if not self.access_token:
            raise ValueError("VK_ACCESS_TOKEN is not set")

        if not self.group_id:
            raise ValueError("VK_GROUP_ID is not set")

        url = f"{self.base_url}/wall.post"

        payload = {
            "owner_id": f"-{self.group_id}",
            "from_group": 1,
            "message": text,
            "access_token": self.access_token,
            "v": self.api_version,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, data=payload)

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"VK API error {error.get('error_code')}: {error.get('error_msg')}"
            )

        return data
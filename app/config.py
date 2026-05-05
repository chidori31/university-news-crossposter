import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Moscow")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    max_bot_token: str = os.getenv("MAX_BOT_TOKEN", "")
    max_chat_id: str = os.getenv("MAX_CHAT_ID", "")

    vk_access_token: str = os.getenv("VK_ACCESS_TOKEN", "")
    vk_group_id: str = os.getenv("VK_GROUP_ID", "")
    vk_api_version: str = os.getenv("VK_API_VERSION", "5.199")


settings = Settings()
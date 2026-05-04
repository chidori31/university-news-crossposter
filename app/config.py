import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    max_bot_token: str = os.getenv("MAX_BOT_TOKEN", "")
    max_chat_id: str = os.getenv("MAX_CHAT_ID", "")


settings = Settings()
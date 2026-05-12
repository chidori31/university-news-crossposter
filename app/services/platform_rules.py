from app.config import settings


def get_platform_statuses() -> list[dict]:
    telegram_ready = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    vk_ready = bool(settings.vk_access_token and settings.vk_group_id)
    max_ready = bool(settings.max_bot_token and settings.max_chat_id)

    return [
        {
            "name": "Telegram",
            "status": "ready" if telegram_ready else "warning",
            "message": "полностью настроен" if telegram_ready else "не настроен",
        },
        {
            "name": "VK",
            "status": "warning" if vk_ready else "error",
            "message": "текст работает, медиа пока отключены" if vk_ready else "не настроен",
        },
        {
            "name": "MAX",
            "status": "ready" if max_ready else "error",
            "message": "настроен" if max_ready else "ожидает токен бота",
        },
    ]


def validate_platform_before_publish(
    platform: str,
    media_files: list[dict],
) -> tuple[bool, str]:
    if platform == "telegram":
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False, "Telegram не настроен: нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID"

        return True, "Telegram готов"

    if platform == "max":
        if not settings.max_bot_token or not settings.max_chat_id:
            return False, "MAX не настроен: нет MAX_BOT_TOKEN или MAX_CHAT_ID"

        return True, "MAX готов"

    if platform == "vk":
        if not settings.vk_access_token or not settings.vk_group_id:
            return False, "VK не настроен: нет VK_ACCESS_TOKEN или VK_GROUP_ID"

        if media_files:
            return False, "VK с медиа пока отключён: текст можно публиковать, фото/видео ждут решения по API"

        return True, "VK готов для текста"

    return False, f"Неизвестная площадка: {platform}"
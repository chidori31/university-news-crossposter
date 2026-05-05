from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.max_client import MaxClient
from app.services.scheduled_posts import (
    add_publish_log,
    get_post_media,
    get_scheduled_posts,
    update_post_status,
)
from app.services.telegram_client import TelegramClient
from app.services.vk_client import VkClient


scheduler = AsyncIOScheduler(timezone=settings.app_timezone)


def should_publish(publish_at: str) -> bool:
    timezone = ZoneInfo(settings.app_timezone)

    planned_time = datetime.fromisoformat(publish_at)

    if planned_time.tzinfo is None:
        planned_time = planned_time.replace(tzinfo=timezone)

    now = datetime.now(timezone)

    return planned_time <= now


async def publish_to_platform(
    platform: str,
    text: str,
    media_files: list[dict],
) -> str:
    if platform == "telegram":
        telegram = TelegramClient()
        await telegram.send_post(text, media_files)
        return "Telegram: опубликовано"

    if platform == "max":
        max_client = MaxClient()
        await max_client.send_post(text, media_files)
        return "MAX: опубликовано"

    if platform == "vk":
        vk_client = VkClient()

        if media_files:
            await vk_client.send_text_with_photos(text, media_files)
        else:
            await vk_client.send_text(text)

        return "VK: опубликовано"

    raise ValueError(f"Unknown platform: {platform}")


async def process_scheduled_posts() -> None:
    posts = get_scheduled_posts()

    for post in posts:
        if not should_publish(post["publish_at"]):
            continue

        post_id = post["id"]
        text = post["text"]
        platforms = post["platforms"]
        media_files = get_post_media(post_id)

        has_errors = False

        update_post_status(post_id, "publishing")

        for platform in platforms:
            try:
                message = await publish_to_platform(
                    platform=platform,
                    text=text,
                    media_files=media_files,
                )

                add_publish_log(
                    post_id=post_id,
                    platform=platform,
                    status="success",
                    message=message,
                )
            except Exception as error:
                has_errors = True

                add_publish_log(
                    post_id=post_id,
                    platform=platform,
                    status="error",
                    message=str(error),
                )

        if has_errors:
            update_post_status(post_id, "failed")
        else:
            update_post_status(post_id, "published")


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        process_scheduled_posts,
        "interval",
        seconds=10,
        id="process_scheduled_posts",
        replace_existing=True,
    )

    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
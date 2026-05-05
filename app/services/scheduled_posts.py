import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.database import get_connection

UPLOADS_DIR = Path("app/static/uploads")


def save_scheduled_post(
    text: str,
    platforms: list[str],
    publish_at: str,
    media_files_data: list[dict],
) -> int:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scheduled_posts (text, platforms, publish_at)
            VALUES (?, ?, ?)
            """,
            (
                text,
                json.dumps(platforms, ensure_ascii=False),
                publish_at,
            ),
        )

        post_id = cursor.lastrowid

        for media in media_files_data:
            extension = Path(media["filename"]).suffix
            stored_filename = f"{uuid4().hex}{extension}"
            file_path = UPLOADS_DIR / stored_filename

            with open(file_path, "wb") as file:
                file.write(media["data"])

            connection.execute(
                """
                INSERT INTO scheduled_post_media (
                    post_id,
                    filename,
                    content_type,
                    kind,
                    file_path
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    media["filename"],
                    media["content_type"],
                    media["kind"],
                    str(file_path),
                ),
            )

        connection.commit()

    return post_id
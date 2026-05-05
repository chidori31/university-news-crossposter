import json
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


def get_scheduled_posts() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, text, platforms, publish_at, status
            FROM scheduled_posts
            WHERE status = 'scheduled'
            ORDER BY publish_at ASC
            """
        ).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "id": row["id"],
            "text": row["text"],
            "platforms": json.loads(row["platforms"]),
            "publish_at": row["publish_at"],
            "status": row["status"],
        })

    return posts


def get_post_media(post_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT filename, content_type, kind, file_path
            FROM scheduled_post_media
            WHERE post_id = ?
            ORDER BY id ASC
            """,
            (post_id,),
        ).fetchall()

    media_files = []

    for row in rows:
        file_path = Path(row["file_path"])

        if not file_path.exists():
            continue

        media_files.append({
            "filename": row["filename"],
            "content_type": row["content_type"],
            "kind": row["kind"],
            "data": file_path.read_bytes(),
        })

    return media_files


def update_post_status(post_id: int, status: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE scheduled_posts
            SET status = ?
            WHERE id = ?
            """,
            (status, post_id),
        )
        connection.commit()


def add_publish_log(
    post_id: int,
    platform: str,
    status: str,
    message: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO publish_logs (post_id, platform, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, platform, status, message),
        )
        connection.commit()

def get_posts_overview(limit: int = 50) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                posts.id,
                posts.text,
                posts.platforms,
                posts.publish_at,
                posts.status,
                posts.created_at,
                COUNT(media.id) AS media_count
            FROM scheduled_posts AS posts
            LEFT JOIN scheduled_post_media AS media
                ON media.post_id = posts.id
            GROUP BY posts.id
            ORDER BY posts.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    result = []

    for row in rows:
        result.append({
            "id": row["id"],
            "text": row["text"],
            "platforms": json.loads(row["platforms"]),
            "publish_at": row["publish_at"],
            "status": row["status"],
            "created_at": row["created_at"],
            "media_count": row["media_count"],
        })

    return result


def cancel_scheduled_post(post_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE scheduled_posts
            SET status = 'cancelled'
            WHERE id = ? AND status = 'scheduled'
            """,
            (post_id,),
        )
        connection.commit()


def get_publish_logs(post_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT platform, status, message, created_at
            FROM publish_logs
            WHERE post_id = ?
            ORDER BY id DESC
            """,
            (post_id,),
        ).fetchall()

    return [
        {
            "platform": row["platform"],
            "status": row["status"],
            "message": row["message"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
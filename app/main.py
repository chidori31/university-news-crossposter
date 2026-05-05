from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from contextlib import asynccontextmanager

from app.database import init_database
from app.services.scheduled_posts import save_scheduled_post

from app.services.telegram_client import TelegramClient
from app.services.max_client import MaxClient
from app.services.vk_client import VkClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="University News Crossposter",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "University News Crossposter is running",
        "create_post_url": "/create",
    }


@app.get("/create", response_class=HTMLResponse)
def create_post_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="create_post.html",
        context={
            "results": None,
            "text": None,
            "selected_platforms": ["telegram"],
        },
    )


@app.post("/create", response_class=HTMLResponse)
async def create_post(
    request: Request,
    text: str = Form(...),
    platforms: list[str] | None = Form(default=None),
    publish_mode: str = Form("now"),
    publish_at: str | None = Form(default=None),
    media_files: list[UploadFile] | None = File(default=None),
):
    selected_platforms = platforms or []
    results = []
    media_files_data = []

    if media_files:
        for file in media_files:
            if not file.filename:
                continue

            if file.content_type and file.content_type.startswith("image/"):
                kind = "image"
            elif file.content_type and file.content_type.startswith("video/"):
                kind = "video"
            else:
                results.append({
                    "platform": "Файл",
                    "message": f"{file.filename}: пока поддерживаются только изображения и видео",
                    "type": "warning",
                })
                continue

            media_files_data.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "kind": kind,
                "data": await file.read(),
            })

    if publish_mode == "schedule":
        if not publish_at:
            results.append({
                "platform": "Ошибка",
                "message": "Укажи дату и время для отложенной публикации",
                "type": "error",
            })
        elif not selected_platforms:
            results.append({
                "platform": "Ошибка",
                "message": "Выбери хотя бы одну площадку для публикации",
                "type": "error",
            })
        else:
            post_id = save_scheduled_post(
                text=text,
                platforms=selected_platforms,
                publish_at=publish_at,
                media_files_data=media_files_data,
            )

            results.append({
                "platform": "Отложка",
                "message": f"публикация сохранена в очередь, ID: {post_id}",
                "type": "success",
            })

        return templates.TemplateResponse(
            request=request,
            name="create_post.html",
            context={
                "results": results,
                "text": text,
                "selected_platforms": selected_platforms,
            },
        )

    if not selected_platforms:
        results.append({
            "platform": "Ошибка",
            "message": "Выбери хотя бы одну площадку для публикации",
            "type": "error",
        })
    else:
        if "telegram" in selected_platforms:
            try:
                telegram = TelegramClient()
                await telegram.send_post(text, media_files_data)

                results.append({
                    "platform": "Telegram",
                    "message": "публикация успешно отправлена",
                    "type": "success",
                })
            except Exception as error:
                results.append({
                    "platform": "Telegram",
                    "message": f"ошибка отправки: {error}",
                    "type": "error",
                })

        if "max" in selected_platforms:
            try:
                max_client = MaxClient()
                await max_client.send_post(text, media_files_data)

                results.append({
                    "platform": "MAX",
                    "message": "публикация успешно отправлена",
                    "type": "success",
                })
            except Exception as error:
                results.append({
                    "platform": "MAX",
                    "message": f"ошибка отправки: {error}",
                    "type": "error",
                })

        if "vk" in selected_platforms:
            try:
                vk_client = VkClient()

                if media_files_data:
                    await vk_client.send_text_with_photos(text, media_files_data)
                else:
                    await vk_client.send_text(text)

                results.append({
                    "platform": "VK",
                    "message": "публикация успешно отправлена",
                    "type": "success",
                })
            except Exception as error:
                results.append({
                    "platform": "VK",
                    "message": f"ошибка отправки: {error}",
                    "type": "error",
                })

    return templates.TemplateResponse(
        request=request,
        name="create_post.html",
        context={
            "results": results,
            "text": text,
            "selected_platforms": selected_platforms,
        },
    )


@app.post("/test-telegram")
async def test_telegram():
    telegram = TelegramClient()

    result = await telegram.send_text(
        "<b>Тестовая публикация</b>\n\n"
        "Это тест отправки новости через University News Crossposter 🚀",
        parse_mode="HTML",
    )

    return {
        "status": "sent",
        "telegram_response": result,
    }
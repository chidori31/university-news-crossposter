from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.database import init_database
from app.services.formatter import prepare_html_text, strip_html_formatting
from app.services.max_client import MaxClient
from app.services.scheduled_posts import (
    cancel_scheduled_post,
    delete_scheduled_post,
    get_post_media_info,
    get_posts_overview,
    get_publish_logs,
    get_scheduled_post,
    save_scheduled_post,
    update_scheduled_post,
)
from app.services.scheduler import shutdown_scheduler, start_scheduler
from app.services.telegram_client import TelegramClient
from app.services.vk_client import VkClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="University News Crossposter",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "University News Crossposter is running",
        "create_post_url": "/create",
        "scheduled_posts_url": "/scheduled",
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
                telegram_text = prepare_html_text(text)

                await telegram.send_post(
                    telegram_text,
                    media_files_data,
                    parse_mode="HTML",
                )

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
                max_text = prepare_html_text(text)

                await max_client.send_post(
                    max_text,
                    media_files_data,
                    text_format="html",
                )

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
                vk_text = strip_html_formatting(text)

                if media_files_data:
                    await vk_client.send_text_with_photos(vk_text, media_files_data)
                else:
                    await vk_client.send_text(vk_text)

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


@app.get("/scheduled", response_class=HTMLResponse)
def scheduled_posts_page(request: Request):
    posts = get_posts_overview()

    for post in posts:
        post["logs"] = get_publish_logs(post["id"])
        post["media"] = get_post_media_info(post["id"])
        post["preview_text"] = prepare_html_text(post["text"])

    return templates.TemplateResponse(
        request=request,
        name="scheduled_posts.html",
        context={
            "posts": posts,
        },
    )


@app.post("/scheduled/{post_id}/cancel")
def cancel_post(post_id: int):
    cancel_scheduled_post(post_id)

    return RedirectResponse(
        url="/scheduled",
        status_code=303,
    )

@app.get("/scheduled/{post_id}/edit", response_class=HTMLResponse)
def edit_scheduled_post_page(request: Request, post_id: int):
    post = get_scheduled_post(post_id)

    if post is None:
        return templates.TemplateResponse(
            request=request,
            name="edit_scheduled_post.html",
            context={
                "post": None,
                "status": "Публикация не найдена",
                "status_type": "error",
            },
        )

    if post["status"] != "scheduled":
        return templates.TemplateResponse(
            request=request,
            name="edit_scheduled_post.html",
            context={
                "post": post,
                "status": "Редактировать можно только отложенные публикации",
                "status_type": "error",
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="edit_scheduled_post.html",
        context={
            "post": post,
            "status": None,
            "status_type": None,
        },
    )


@app.post("/scheduled/{post_id}/edit", response_class=HTMLResponse)
def edit_scheduled_post(
    request: Request,
    post_id: int,
    text: str = Form(...),
    platforms: list[str] | None = Form(default=None),
    publish_at: str = Form(...),
):
    selected_platforms = platforms or []
    post = get_scheduled_post(post_id)

    if post is None:
        return templates.TemplateResponse(
            request=request,
            name="edit_scheduled_post.html",
            context={
                "post": None,
                "status": "Публикация не найдена",
                "status_type": "error",
            },
        )

    if post["status"] != "scheduled":
        return templates.TemplateResponse(
            request=request,
            name="edit_scheduled_post.html",
            context={
                "post": post,
                "status": "Редактировать можно только отложенные публикации",
                "status_type": "error",
            },
        )

    if not selected_platforms:
        post["text"] = text
        post["publish_at"] = publish_at
        post["platforms"] = selected_platforms

        return templates.TemplateResponse(
            request=request,
            name="edit_scheduled_post.html",
            context={
                "post": post,
                "status": "Выбери хотя бы одну площадку",
                "status_type": "error",
            },
        )

    update_scheduled_post(
        post_id=post_id,
        text=text,
        platforms=selected_platforms,
        publish_at=publish_at,
    )

    updated_post = get_scheduled_post(post_id)

    return templates.TemplateResponse(
        request=request,
        name="edit_scheduled_post.html",
        context={
            "post": updated_post,
            "status": "Публикация обновлена",
            "status_type": None,
        },
    )


@app.post("/scheduled/{post_id}/delete")
def delete_post(post_id: int):
    delete_scheduled_post(post_id)

    return RedirectResponse(
        url="/scheduled",
        status_code=303,
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
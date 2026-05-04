from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.telegram_client import TelegramClient

app = FastAPI(title="University News Crossposter")

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "University News Crossposter is running",
        "create_post_url": "/create"
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
        }
    )


@app.post("/create", response_class=HTMLResponse)
async def create_post(
    request: Request,
    text: str = Form(...),
    platforms: list[str] | None = Form(default=None),
):
    selected_platforms = platforms or []
    results = []

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
                await telegram.send_text(text)

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
            results.append({
                "platform": "MAX",
                "message": "адаптер пока не подключён",
                "type": "warning",
            })

        if "vk" in selected_platforms:
            results.append({
                "platform": "VK",
                "message": "адаптер пока не подключён",
                "type": "warning",
            })

    return templates.TemplateResponse(
        request=request,
        name="create_post.html",
        context={
            "results": results,
            "text": text,
            "selected_platforms": selected_platforms,
        }
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
        "telegram_response": result
    }
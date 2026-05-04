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
            "status": None,
            "text": None,
        }
    )


@app.post("/create", response_class=HTMLResponse)
async def create_post(request: Request, text: str = Form(...)):
    telegram = TelegramClient()
    await telegram.send_text(text)

    return templates.TemplateResponse(
        request=request,
        name="create_post.html",
        context={
            "status": "Публикация отправлена в Telegram",
            "text": text,
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
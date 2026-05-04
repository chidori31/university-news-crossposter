from fastapi import FastAPI

app = FastAPI(title="University News Crossposter")


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "University News Crossposter is running"
    }

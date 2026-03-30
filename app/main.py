import os
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .services import transcribe_instagram_url, validate_instagram_url

app = FastAPI(title="Instagram Reel Transcriber")

BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Instagram Reel Transcriber"},
    )


@app.get("/health")
def health():
    return {
        "ok": True,
        "has_resolver_url": bool(os.getenv("INSTAGRAM_RESOLVER_URL")),
        "whisper_model_size": os.getenv("WHISPER_MODEL_SIZE", "tiny"),
    }


@app.post("/api/transcribe")
def api_transcribe(url: str = Form(...), language: str = Form("pt")):
    if not validate_instagram_url(url):
        raise HTTPException(status_code=400, detail="URL inválida. Envie um link do Instagram.")

    try:
        result = transcribe_instagram_url(url=url, language=language)
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha interna ao transcrever o vídeo. {exc}") from exc

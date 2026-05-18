import os
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .services import (
    get_configuration_status,
    transcribe_instagram_url,
    validate_instagram_url,
)

app = FastAPI(title="Instagram Reel Transcriber")

BASE_DIR = os.path.dirname(__file__)
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)
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
    configuration = get_configuration_status()
    return {
        "ok": True,
        "configuration_ok": configuration["ok"],
        "resolver_url_configured": configuration["resolver"]["url_source"]
        == "environment",
        "resolver_url_source": configuration["resolver"]["url_source"],
        "has_resolver_token": configuration["resolver"]["has_token"],
        "whisper_model_size": configuration["whisper"]["model_size"],
        "resolver_host": configuration["resolver"]["host"],
        "pending": configuration["pending"],
        "warnings": configuration["warnings"],
    }


@app.get("/api/config-check")
def config_check():
    return get_configuration_status()


@app.post("/api/transcribe")
def api_transcribe(url: str = Form(...), language: str = Form("pt")):
    if not validate_instagram_url(url):
        raise HTTPException(
            status_code=400, detail="URL inválida. Envie um link do Instagram."
        )

    try:
        result = transcribe_instagram_url(url=url, language=language)
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Falha interna ao transcrever o vídeo. {exc}"
        ) from exc

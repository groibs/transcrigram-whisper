import os
import re
import tempfile
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import requests
from faster_whisper import WhisperModel

ALLOWED_HOSTS = {"instagram.com", "www.instagram.com"}
DEFAULT_INSTAGRAM_RESOLVER_URL = (
    "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"
)
SUPPORTED_MEDIA_KEYS = [
    "media_url",
    "video_url",
    "videoUrl",
    "download_url",
    "downloadUrl",
    "displayUrl",
    "video_url_hd",
    "contentUrl",
    "url",
    "direct_url",
]
VALID_WHISPER_MODEL_SIZES = {
    "tiny",
    "base",
    "small",
    "medium",
    "large-v1",
    "large-v2",
    "large-v3",
}


def validate_instagram_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() not in ALLOWED_HOSTS:
        return False

    path = parsed.path.lower()
    return (
        path.startswith("/reel/") or path.startswith("/p/") or path.startswith("/tv/")
    )


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    size = get_whisper_model_size()
    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe_instagram_url(url: str, language: str = "pt") -> dict[str, Any]:
    media_url = resolve_media_url(url)
    normalized_language = normalize_language(language)
    text = transcribe_media_from_url(media_url, language=normalized_language)
    return {
        "source_url": url,
        "media_url": media_url,
        "language": normalized_language or "auto",
        "text": text.strip(),
    }


def resolve_media_url(instagram_url: str) -> str:
    resolver_url = get_resolver_url()
    resolver_token = get_resolver_token()
    resolver_auth_header = get_resolver_auth_header()

    if is_apify_resolver(resolver_url) and not resolver_token:
        raise RuntimeError(
            "INSTAGRAM_RESOLVER_TOKEN não configurada. "
            "No Vercel, adicione a variável de ambiente com o valor Bearer apify_api_xxxxx."
        )

    headers = {"Accept": "application/json"}
    if resolver_token:
        headers[resolver_auth_header] = resolver_token

    payload = build_resolver_payload(
        resolver_url=resolver_url, instagram_url=instagram_url
    )

    response = requests.post(resolver_url, json=payload, headers=headers, timeout=180)

    if response.status_code >= 400:
        raise RuntimeError(
            f"A API externa falhou ao resolver a mídia do Instagram. HTTP {response.status_code}."
        )

    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError("A API externa retornou uma resposta inválida.") from exc

    media_url = extract_media_url(payload)
    if not media_url:
        raise RuntimeError("A API externa não devolveu uma URL de mídia utilizável.")

    return media_url


def get_resolver_url() -> str:
    return (
        os.getenv("INSTAGRAM_RESOLVER_URL", DEFAULT_INSTAGRAM_RESOLVER_URL).strip()
        or DEFAULT_INSTAGRAM_RESOLVER_URL
    )


def get_resolver_token() -> str:
    return os.getenv("INSTAGRAM_RESOLVER_TOKEN", "").strip()


def get_resolver_auth_header() -> str:
    return (
        os.getenv("INSTAGRAM_RESOLVER_AUTH_HEADER", "Authorization").strip()
        or "Authorization"
    )


def get_whisper_model_size() -> str:
    return os.getenv("WHISPER_MODEL_SIZE", "tiny").strip() or "tiny"


def is_apify_resolver(resolver_url: str) -> bool:
    parsed = urlparse(resolver_url)
    return (
        "api.apify.com" in parsed.netloc.lower()
        and "/acts/apify~instagram-scraper/" in parsed.path.lower()
    )


def build_resolver_payload(resolver_url: str, instagram_url: str) -> dict[str, Any]:
    if is_apify_resolver(resolver_url):
        return {
            "directUrls": [instagram_url],
            "resultsType": "reels",
            "resultsLimit": 1,
        }

    return {"url": instagram_url}


def get_configuration_status() -> dict[str, Any]:
    resolver_url = get_resolver_url()
    resolver_token = get_resolver_token()
    resolver_auth_header = get_resolver_auth_header()
    whisper_model_size = get_whisper_model_size()
    using_apify = is_apify_resolver(resolver_url)

    pending: list[str] = []
    warnings: list[str] = []

    if using_apify and not resolver_token:
        pending.append(
            "Definir INSTAGRAM_RESOLVER_TOKEN com o valor no formato 'Bearer apify_api_xxxxx'."
        )
    if (
        using_apify
        and resolver_token
        and not resolver_token.lower().startswith("bearer ")
    ):
        warnings.append(
            "INSTAGRAM_RESOLVER_TOKEN está configurada, mas para Apify o formato esperado é 'Bearer apify_api_xxxxx'."
        )
    if not using_apify and not os.getenv("INSTAGRAM_RESOLVER_URL", "").strip():
        pending.append(
            "Definir INSTAGRAM_RESOLVER_URL para o resolvedor externo escolhido."
        )
    if not using_apify and not resolver_token:
        warnings.append(
            "INSTAGRAM_RESOLVER_TOKEN está vazia; isso só funciona se o resolvedor externo não exigir autenticação."
        )
    if resolver_auth_header != "Authorization" and using_apify:
        warnings.append(
            "INSTAGRAM_RESOLVER_AUTH_HEADER deve ser 'Authorization' ao usar Apify."
        )
    if whisper_model_size not in VALID_WHISPER_MODEL_SIZES:
        warnings.append(
            f"WHISPER_MODEL_SIZE='{whisper_model_size}' não é um tamanho padrão do faster-whisper."
        )

    return {
        "ok": not pending,
        "pending": pending,
        "warnings": warnings,
        "resolver": {
            "url_source": (
                "environment"
                if os.getenv("INSTAGRAM_RESOLVER_URL", "").strip()
                else "default_apify"
            ),
            "host": urlparse(resolver_url).netloc or "invalid",
            "is_apify": using_apify,
            "has_token": bool(resolver_token),
            "auth_header": resolver_auth_header,
        },
        "whisper": {
            "model_size": whisper_model_size,
        },
    }


def extract_media_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in SUPPORTED_MEDIA_KEYS:
            value = payload.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

        for key in ("data", "result", "results"):
            if key in payload:
                found = extract_media_url(payload[key])
                if found:
                    return found

    if isinstance(payload, list):
        for item in payload:
            found = extract_media_url(item)
            if found:
                return found

    return None


def transcribe_media_from_url(media_url: str, language: str | None = "pt") -> str:
    with tempfile.NamedTemporaryFile(
        delete=True, suffix=guess_extension(media_url)
    ) as temp_file:
        download_media(media_url, temp_file.name)
        return transcribe_file_local(temp_file.name, language=language)


def guess_extension(url: str) -> str:
    path = urlparse(url).path.lower()
    match = re.search(r"(\.mp4|\.mp3|\.m4a|\.wav|\.webm|\.mpeg|\.mpga)$", path)
    if match:
        return match.group(1)
    return ".mp4"


def download_media(media_url: str, destination: str) -> None:
    with requests.get(media_url, stream=True, timeout=180) as response:
        if response.status_code >= 400:
            raise RuntimeError(
                f"Falha ao baixar a mídia para transcrição. HTTP {response.status_code}."
            )

        with open(destination, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def normalize_language(language: str | None) -> str | None:
    if language is None:
        return None
    normalized = language.strip().lower()
    if not normalized or normalized == "auto":
        return None
    return normalized


def transcribe_file_local(file_path: str, language: str | None = "pt") -> str:
    model = get_whisper_model()
    segments, _info = model.transcribe(
        file_path, language=normalize_language(language), vad_filter=True
    )
    text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
    if not text_parts:
        raise RuntimeError("O Whisper local não devolveu texto transcrito.")
    return " ".join(text_parts)

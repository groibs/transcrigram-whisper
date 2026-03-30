import os
import re
import tempfile
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import requests
from faster_whisper import WhisperModel

ALLOWED_HOSTS = {"instagram.com", "www.instagram.com"}
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
    return path.startswith("/reel/") or path.startswith("/p/") or path.startswith("/tv/")


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    size = os.getenv("WHISPER_MODEL_SIZE", "tiny").strip() or "tiny"
    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe_instagram_url(url: str, language: str = "pt") -> dict[str, Any]:
    media_url = resolve_media_url(url)
    text = transcribe_media_from_url(media_url, language=language)
    return {
        "source_url": url,
        "media_url": media_url,
        "language": language,
        "text": text.strip(),
    }


def resolve_media_url(instagram_url: str) -> str:
    resolver_url = os.getenv("INSTAGRAM_RESOLVER_URL", "").strip()
    resolver_token = os.getenv("INSTAGRAM_RESOLVER_TOKEN", "").strip()
    resolver_auth_header = os.getenv("INSTAGRAM_RESOLVER_AUTH_HEADER", "Authorization").strip() or "Authorization"

    if not resolver_url:
        raise RuntimeError("INSTAGRAM_RESOLVER_URL não configurada.")

    headers = {"Accept": "application/json"}
    if resolver_token:
        headers[resolver_auth_header] = resolver_token

    payload = build_resolver_payload(resolver_url=resolver_url, instagram_url=instagram_url)

    response = requests.post(resolver_url, json=payload, headers=headers, timeout=180)

    if response.status_code >= 400:
        raise RuntimeError(f"A API externa falhou ao resolver a mídia do Instagram. HTTP {response.status_code}.")

    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError("A API externa retornou uma resposta inválida.") from exc

    media_url = extract_media_url(payload)
    if not media_url:
        raise RuntimeError("A API externa não devolveu uma URL de mídia utilizável.")

    return media_url


def build_resolver_payload(resolver_url: str, instagram_url: str) -> dict[str, Any]:
    parsed = urlparse(resolver_url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if "api.apify.com" in host and "/acts/apify~instagram-scraper/" in path:
        return {
            "directUrls": [instagram_url],
            "resultsType": "reels",
            "resultsLimit": 1,
        }

    return {"url": instagram_url}


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


def transcribe_media_from_url(media_url: str, language: str = "pt") -> str:
    with tempfile.NamedTemporaryFile(delete=True, suffix=guess_extension(media_url)) as temp_file:
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
            raise RuntimeError(f"Falha ao baixar a mídia para transcrição. HTTP {response.status_code}.")

        with open(destination, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def transcribe_file_local(file_path: str, language: str = "pt") -> str:
    model = get_whisper_model()
    segments, _info = model.transcribe(file_path, language=language, vad_filter=True)
    text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
    if not text_parts:
        raise RuntimeError("O Whisper local não devolveu texto transcrito.")
    return " ".join(text_parts)

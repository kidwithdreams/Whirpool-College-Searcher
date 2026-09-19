from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    # Windows PowerShell commonly creates UTF-16 .env files. Detect the BOM so
    # secrets can be loaded without reading, rewriting, or logging their values.
    with path.open("rb") as stream:
        bom = stream.read(2)
    encoding = "utf-16" if bom in {b"\xff\xfe", b"\xfe\xff"} else "utf-8"
    load_dotenv(path, override=False, encoding=encoding)


# A backend-local file wins; the existing project-level .env remains a fallback.
_load_env_file(BACKEND_ROOT / ".env")
_load_env_file(PROJECT_ROOT / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    ai_provider: str = field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "auto").strip().lower()
    )
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip(), repr=False
    )
    yandex_api_key: str = field(
        default_factory=lambda: os.getenv("YANDEX_API_KEY", "").strip(), repr=False
    )
    yandex_folder_id: str = field(
        default_factory=lambda: os.getenv("YANDEX_FOLDER_ID", "").strip()
    )
    yandex_model: str = field(
        default_factory=lambda: os.getenv("YANDEX_MODEL", "yandexgpt").strip()
    )
    search_api_key: str = field(
        default_factory=lambda: os.getenv("SEARCH_API_KEY", "").strip(), repr=False
    )
    search_api_key_fallback: str = field(
        default_factory=lambda: os.getenv("SEARCH_API_KEY_FALLBACK", "").strip(),
        repr=False,
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv(
            "GEMINI_MODEL", "gemini-3.5-flash-lite"
        ).strip()
    )
    search_api_url: str = field(
        default_factory=lambda: os.getenv(
            "SEARCH_API_URL", "https://google.serper.dev/images"
        ).strip()
    )
    search_results_per_query: int = field(
        default_factory=lambda: _int("SEARCH_RESULTS_PER_QUERY", 10)
    )
    nominatim_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "NOMINATIM_USER_AGENT",
            "WhirlpoolCampusProfiler/1.0",
        ).strip()
    )
    cors_origins_raw: str = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,"
            "https://whirlpool-campus-profiler.rozasadykovas.chatgpt.site",
        )
    )
    pipeline_timeout_seconds: float = field(
        default_factory=lambda: _float("PIPELINE_TIMEOUT_SECONDS", 29.0)
    )
    max_images: int = field(default_factory=lambda: _int("MAX_IMAGES", 16))

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins_raw.split(",") if value.strip()]

    @property
    def search_api_keys(self) -> list[str]:
        # Preserve order while avoiding accidental duplicate requests with one key.
        return list(
            dict.fromkeys(
                key for key in (self.search_api_key, self.search_api_key_fallback) if key
            )
        )

    @property
    def resolved_ai_provider(self) -> str:
        if self.ai_provider in {"gemini", "yandex"}:
            return self.ai_provider
        if self.yandex_api_key and self.yandex_folder_id:
            return "yandex"
        return "gemini"

    @property
    def missing_required_keys(self) -> list[str]:
        missing: list[str] = []
        if self.resolved_ai_provider == "yandex":
            if not self.yandex_api_key:
                missing.append("YANDEX_API_KEY")
            if not self.yandex_folder_id:
                missing.append("YANDEX_FOLDER_ID")
        elif not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.search_api_keys:
            missing.append("SEARCH_API_KEY")
        return missing

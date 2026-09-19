from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from io import BytesIO
from urllib.parse import urlparse

import httpx
import imagehash
import numpy as np
from PIL import Image, ImageOps

from app.config import Settings
from app.models import UniversityImage
from app.services.clip import ClipEmbedder


logger = logging.getLogger(__name__)
Image.MAX_IMAGE_PIXELS = 40_000_000

SEARCH_SUFFIXES = (
    "campus exterior building",
    "student dormitory room",
    "laboratory lecture hall library",
    "student life sports facility",
)

CATEGORY_KEYWORDS = {
    "Campus": ("campus", "building", "exterior", "quad"),
    "Dormitories": ("dorm", "dormitory", "residence", "housing", "room"),
    "Laboratories": ("laboratory", "lab", "lecture hall", "library"),
    "Sports": ("sport", "stadium", "gym", "athletic", "pool"),
    "Student Life": ("student life", "students", "club", "society", "event"),
}


@dataclass(slots=True)
class ImageCandidate:
    image_url: str
    source_page_url: str
    title: str
    snippet: str
    source_name: str
    published_date: str


@dataclass(slots=True)
class DownloadedImage:
    candidate: ImageCandidate
    image: Image.Image
    phash: str


def _first_string(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_search_payload(payload: object) -> list[ImageCandidate]:
    """Parse Serper plus common image-search response field aliases."""
    if not isinstance(payload, dict):
        return []
    rows: object = payload.get("images") or payload.get("items") or payload.get("results") or []
    if not isinstance(rows, list):
        return []
    candidates: list[ImageCandidate] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        image_url = _first_string(
            item, "imageUrl", "image_url", "original", "thumbnailUrl", "thumbnail"
        )
        source_url = _first_string(
            item, "link", "source_page_url", "sourceUrl", "pageUrl", "hostPageUrl"
        )
        if not image_url or not source_url:
            continue
        candidates.append(
            ImageCandidate(
                image_url=image_url,
                source_page_url=source_url,
                title=_first_string(item, "title", "name"),
                snippet=_first_string(item, "snippet", "description", "caption"),
                source_name=_first_string(item, "source", "source_name", "domain"),
                published_date=_first_string(item, "date", "publishedDate", "published_date"),
            )
        )
    return candidates


async def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if any(
            (
                address.is_private,
                address.is_loopback,
                address.is_link_local,
                address.is_reserved,
                address.is_multicast,
                address.is_unspecified,
            )
        ):
            return False
    return bool(infos)


def keyword_category(candidate: ImageCandidate) -> str:
    haystack = f"{candidate.title} {candidate.snippet}".lower()
    scored = {
        category: sum(keyword in haystack for keyword in keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best = max(scored, key=scored.get)
    return best if scored[best] else "Campus"


def normalized_date(raw: str) -> str:
    if not raw:
        return date.today().isoformat()
    candidate = raw.strip()
    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        try:
            return parsedate_to_datetime(candidate).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            return date.today().isoformat()


def confidence_for(
    candidate: ImageCandidate, university_name: str, category: str
) -> tuple[int, bool]:
    hostname = (urlparse(candidate.source_page_url).hostname or "").lower()
    official_domain = (
        hostname.endswith(".edu")
        or ".edu." in hostname
        or hostname.endswith(".ac.uk")
        or hostname.endswith(".kz")
    )
    haystack = f"{candidate.title} {candidate.snippet} {candidate.source_page_url}".lower()
    university_match = university_name.lower() in haystack
    category_match = any(
        keyword in haystack for keyword in CATEGORY_KEYWORDS.get(category, ())
    )

    score = 48
    score += 38 if official_domain else 0
    score += 12 if university_match else 0
    score += 10 if category_match else 0
    if official_domain or (university_match and category_match):
        score = max(score, 86)
    score = min(score, 99)
    return score, score >= 85


class ImagePipeline:
    def __init__(
        self, settings: Settings, client: httpx.AsyncClient, clip: ClipEmbedder
    ) -> None:
        self.settings = settings
        self.client = client
        self.clip = clip
        self._download_limit = asyncio.Semaphore(8)
        self._key_lock = asyncio.Lock()
        self._next_key_index = 0

    async def _ordered_api_keys(self) -> list[str]:
        keys = self.settings.search_api_keys
        if len(keys) < 2:
            return keys
        async with self._key_lock:
            start = self._next_key_index % len(keys)
            self._next_key_index += 1
        return keys[start:] + keys[:start]

    async def _search(self, query: str) -> list[ImageCandidate]:
        last_response: httpx.Response | None = None
        for api_key in await self._ordered_api_keys():
            response = await self.client.post(
                self.settings.search_api_url,
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": self.settings.search_results_per_query},
                timeout=5.0,
            )
            last_response = response
            if response.status_code not in {401, 403, 429}:
                response.raise_for_status()
                return parse_search_payload(response.json())
        if last_response is not None:
            last_response.raise_for_status()
        return []

    async def _download(self, candidate: ImageCandidate) -> DownloadedImage | None:
        if not await _is_public_http_url(candidate.image_url):
            return None
        try:
            async with self._download_limit:
                async with self.client.stream(
                    "GET", candidate.image_url, follow_redirects=True, timeout=5.0
                ) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if content_type and not content_type.startswith("image/"):
                        return None
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 8_000_000:
                            return None
                        chunks.append(chunk)
            raw = b"".join(chunks)
            image = await asyncio.to_thread(self._decode_image, raw)
            phash = await asyncio.to_thread(lambda: str(imagehash.phash(image)))
            return DownloadedImage(candidate, image, phash)
        except (httpx.HTTPError, OSError, ValueError, Image.DecompressionBombError):
            return None

    @staticmethod
    def _decode_image(raw: bytes) -> Image.Image:
        with Image.open(BytesIO(raw)) as opened:
            normalized = ImageOps.exif_transpose(opened).convert("RGB")
            normalized.thumbnail((1280, 1280))
            return normalized.copy()

    async def run(self, university_name: str) -> list[UniversityImage]:
        searches = await asyncio.gather(
            *(self._search(f"{university_name} {suffix}") for suffix in SEARCH_SUFFIXES),
            return_exceptions=True,
        )
        candidates: list[ImageCandidate] = []
        seen_urls: set[str] = set()
        for result in searches:
            if isinstance(result, Exception):
                logger.warning("Image search request failed: %s", type(result).__name__)
                continue
            for candidate in result:
                if candidate.image_url not in seen_urls:
                    seen_urls.add(candidate.image_url)
                    candidates.append(candidate)

        # Bound download and CLIP work so the request can meet its deadline.
        candidates = candidates[: max(self.settings.max_images * 2, 24)]
        downloads = await asyncio.gather(
            *(self._download(candidate) for candidate in candidates),
            return_exceptions=True,
        )
        exact_unique: list[DownloadedImage] = []
        hashes: set[str] = set()
        for downloaded in downloads:
            if not isinstance(downloaded, DownloadedImage) or downloaded.phash in hashes:
                continue
            hashes.add(downloaded.phash)
            exact_unique.append(downloaded)

        if not exact_unique:
            return []

        embeddings = await asyncio.to_thread(
            self.clip.encode_images, [item.image for item in exact_unique]
        )
        if embeddings.size:
            categories = self.clip.categories_for(embeddings)
            keep_indices: list[int] = []
            for index, embedding in enumerate(embeddings):
                if not keep_indices:
                    keep_indices.append(index)
                    continue
                similarities = embeddings[keep_indices] @ embedding
                if float(np.max(similarities)) <= 0.90:
                    keep_indices.append(index)
        else:
            categories = [keyword_category(item.candidate) for item in exact_unique]
            keep_indices = list(range(len(exact_unique)))

        output: list[UniversityImage] = []
        for index in keep_indices[: self.settings.max_images]:
            item = exact_unique[index]
            category = categories[index]
            confidence, verified = confidence_for(item.candidate, university_name, category)
            hostname = urlparse(item.candidate.source_page_url).hostname or "Unknown source"
            output.append(
                UniversityImage(
                    id=f"img_{len(output) + 1:02d}",
                    url=item.candidate.image_url,
                    category=category,
                    source_name=item.candidate.source_name or hostname,
                    source_url=item.candidate.source_page_url,
                    date=normalized_date(item.candidate.published_date),
                    confidence=confidence,
                    is_verified=verified,
                )
            )
        return output

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from typing import TypeVar

import httpx

from app.config import Settings
from app.models import SearchResponse, Stats, UniversityImage
from app.services.clip import ClipEmbedder
from app.services.images import ImagePipeline
from app.services.metadata import MetadataPipeline, MetadataResult, NominatimClient
from app.services.summary import SummaryPipeline


logger = logging.getLogger(__name__)
T = TypeVar("T")


async def _bounded(
    name: str, awaitable: Awaitable[T], timeout_seconds: float, fallback: T
) -> T:
    try:
        async with asyncio.timeout(timeout_seconds):
            return await awaitable
    except Exception as exc:
        logger.warning("%s stream returned its safe fallback: %s", name, type(exc).__name__)
        return fallback


class WhirlpoolPipeline:
    def __init__(
        self, settings: Settings, client: httpx.AsyncClient, clip: ClipEmbedder
    ) -> None:
        self.settings = settings
        self.images = ImagePipeline(settings, client, clip)
        self.summary = SummaryPipeline(settings, client)
        self.metadata = MetadataPipeline(NominatimClient(settings, client))

    async def run(self, university_name: str) -> SearchResponse:
        unavailable_metadata = MetadataResult(
            location="Location unavailable",
            stats=Stats(
                distance_to_city_center="Unavailable",
                climate="Unavailable",
                avg_living_cost="Unavailable",
            ),
            found=False,
        )
        image_result, summary_result, metadata_result = await asyncio.gather(
            _bounded("image", self.images.run(university_name), 15.0, []),
            _bounded(
                "summary",
                self.summary.run(university_name),
                22.0,
                "A reliable campus summary could not be generated within the time limit.",
            ),
            _bounded(
                "metadata", self.metadata.run(university_name), 26.0, unavailable_metadata
            ),
        )

        images = image_result if isinstance(image_result, list) else []
        summary = str(summary_result)
        metadata = (
            metadata_result
            if isinstance(metadata_result, MetadataResult)
            else unavailable_metadata
        )
        confidence = self._overall_confidence(images, summary, metadata)
        return SearchResponse(
            university_name=university_name,
            location=metadata.location,
            summary=summary,
            confidence_score=confidence,
            stats=metadata.stats,
            images=images,
        )

    @staticmethod
    def _overall_confidence(
        images: list[UniversityImage], summary: str, metadata: MetadataResult
    ) -> int:
        signals: list[float] = []
        if images:
            signals.append(sum(image.confidence for image in images) / len(images))
        if summary and "could not" not in summary.lower():
            signals.append(88.0)
        if metadata.found:
            signals.append(92.0)
        return round(sum(signals) / len(signals)) if signals else 0

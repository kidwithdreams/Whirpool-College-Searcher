from __future__ import annotations

import asyncio
import re

import httpx

from app.config import Settings


SUMMARY_PROMPT = (
    "Generate a concise 3-sentence summary in English about the university "
    "campus, buildings, and facilities based on this context. Do not invent "
    "facts; if the context is incomplete, state that uncertainty.\n\nContext:\n"
)


def first_three_sentences(text: str) -> str:
    compact = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    return " ".join(sentence for sentence in sentences[:3] if sentence).strip()


class SummaryPipeline:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def _wikipedia(self, university_name: str) -> str:
        response = await self.client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "redirects": "1",
                "titles": university_name,
                "format": "json",
            },
            timeout=5.0,
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        if not isinstance(pages, dict):
            return ""
        return " ".join(
            page.get("extract", "") for page in pages.values() if isinstance(page, dict)
        ).strip()

    async def _duckduckgo(self, university_name: str) -> str:
        response = await self.client.get(
            "https://api.duckduckgo.com/",
            params={
                "q": university_name,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            },
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
        return " ".join(
            value
            for value in (payload.get("AbstractText"), payload.get("Answer"))
            if isinstance(value, str) and value.strip()
        )

    async def _generate_gemini(self, context: str) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            # The 120-token ceiling includes thought tokens. Flash-Lite supports
            # minimal thinking; 3.7/3.8 Flash require low as their minimum.
            thinking_level = (
                "low"
                if self.settings.gemini_model.startswith(("gemini-3.7", "gemini-3.8"))
                else "minimal"
            )
            response = await client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=SUMMARY_PROMPT + context[:12_000],
                config=types.GenerateContentConfig(
                    max_output_tokens=120,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=thinking_level
                    ),
                ),
            )
            return first_three_sentences(response.text or "")
        finally:
            close = getattr(client.aio, "aclose", None)
            if close is not None:
                await close()

    async def _generate_yandex(self, context: str) -> str:
        model_uri = (
            f"gpt://{self.settings.yandex_folder_id}/"
            f"{self.settings.yandex_model}/latest"
        )
        response = await self.client.post(
            "https://ai.api.cloud.yandex.net/v1/chat/completions",
            headers={
                # Yandex's OpenAI-compatible endpoint follows OpenAI's Bearer
                # authentication convention. Native Yandex APIs use Api-Key.
                "Authorization": f"Bearer {self.settings.yandex_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_uri,
                "messages": [
                    {
                        "role": "user",
                        "content": SUMMARY_PROMPT + context[:12_000],
                    }
                ],
                "max_tokens": 120,
                "temperature": 0.2,
                "stream": False,
            },
            timeout=12.0,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices", [])
        if not choices:
            return ""
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        return first_three_sentences(content if isinstance(content, str) else "")

    async def _generate(self, context: str) -> str:
        if self.settings.resolved_ai_provider == "yandex":
            return await self._generate_yandex(context)
        return await self._generate_gemini(context)

    async def run(self, university_name: str) -> str:
        sources = await asyncio.gather(
            self._wikipedia(university_name),
            self._duckduckgo(university_name),
            return_exceptions=True,
        )
        raw_parts = [part for part in sources if isinstance(part, str) and part.strip()]
        context = "\n\n".join(raw_parts)
        if not context:
            return "No reliable campus description was available from the selected public sources. Facilities could not be verified from the available context. Review the linked image sources directly before making a decision."
        try:
            generated = await self._generate(context)
            return generated or first_three_sentences(context)
        except Exception:
            # Degrade safely when Gemini is unavailable instead of fabricating text.
            return first_three_sentences(context)

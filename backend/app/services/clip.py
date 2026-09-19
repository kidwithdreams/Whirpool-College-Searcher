from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)

CATEGORY_PROMPTS = {
    "Campus": "a photo of a university campus exterior and academic buildings",
    "Dormitories": "a photo of a university student dormitory or residence room",
    "Laboratories": "a photo of a university laboratory, lecture hall, or library",
    "Sports": "a photo of university sports facilities or athletics",
    "Student Life": "a photo of university students and student life activities",
}


class ClipEmbedder:
    """Small OpenCLIP wrapper with normalized embeddings and cached category vectors."""

    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._torch = None
        self._device = "cpu"
        self.category_names = list(CATEGORY_PROMPTS)
        self.category_embeddings: np.ndarray | None = None

    def initialize(self) -> None:
        try:
            import open_clip
            import torch

            self._torch = torch
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="laion2b_s34b_b79k"
            )
            self._model = model.to(self._device).eval()
            self._preprocess = preprocess
            self._tokenizer = open_clip.get_tokenizer("ViT-B-32")
            tokens = self._tokenizer(list(CATEGORY_PROMPTS.values())).to(self._device)
            with torch.inference_mode():
                text_features = self._model.encode_text(tokens)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            self.category_embeddings = text_features.cpu().numpy()
            self.available = True
        except Exception as exc:  # startup remains available with an honest fallback
            self.error = f"{type(exc).__name__}: {exc}"
            logger.warning("CLIP initialization failed; using keyword categories: %s", self.error)

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray:
        if not self.available or not images:
            return np.empty((0, 0), dtype=np.float32)
        assert self._torch is not None
        assert self._model is not None
        assert self._preprocess is not None
        batch = self._torch.stack([self._preprocess(image) for image in images]).to(
            self._device
        )
        with self._torch.inference_mode():
            features = self._model.encode_image(batch)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy()

    def categories_for(self, embeddings: np.ndarray) -> list[str]:
        if embeddings.size == 0 or self.category_embeddings is None:
            return []
        indices = np.argmax(embeddings @ self.category_embeddings.T, axis=1)
        return [self.category_names[int(index)] for index in indices]

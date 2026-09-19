from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    university_name: str = Field(min_length=2, max_length=160)

    @field_validator("university_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("university_name cannot be blank")
        return value


class Stats(BaseModel):
    distance_to_city_center: str
    climate: str
    avg_living_cost: str


class UniversityImage(BaseModel):
    id: str
    url: str
    category: str
    source_name: str
    source_url: str
    date: str
    confidence: int = Field(ge=0, le=100)
    is_verified: bool


class SearchResponse(BaseModel):
    university_name: str
    location: str
    summary: str
    confidence_score: int = Field(ge=0, le=100)
    stats: Stats
    images: list[UniversityImage]

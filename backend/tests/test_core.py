from app.models import SearchRequest
from app.services.images import ImageCandidate, confidence_for, parse_search_payload
from app.services.metadata import haversine_km


def test_request_normalizes_whitespace() -> None:
    request = SearchRequest(university_name="  Nazarbayev   University ")
    assert request.university_name == "Nazarbayev University"


def test_serper_payload_parser() -> None:
    parsed = parse_search_payload(
        {
            "images": [
                {
                    "imageUrl": "https://cdn.example/image.jpg",
                    "link": "https://nu.edu.kz/campus",
                    "title": "Nazarbayev University campus",
                    "source": "NU",
                }
            ]
        }
    )
    assert len(parsed) == 1
    assert parsed[0].source_page_url == "https://nu.edu.kz/campus"


def test_official_domain_is_verified() -> None:
    candidate = ImageCandidate(
        image_url="https://cdn.example/campus.jpg",
        source_page_url="https://nu.edu.kz/campus",
        title="Nazarbayev University campus exterior",
        snippet="Main building",
        source_name="NU",
        published_date="",
    )
    confidence, verified = confidence_for(candidate, "Nazarbayev University", "Campus")
    assert confidence >= 85
    assert verified is True


def test_haversine_distance() -> None:
    # Roughly one degree of longitude at the equator.
    assert 110.0 < haversine_km(0, 0, 0, 1) < 112.0

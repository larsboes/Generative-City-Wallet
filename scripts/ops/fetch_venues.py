import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from spark.db.connection import upsert_venues  # noqa: E402
from spark.services.canonicalization import normalize_category  # noqa: E402


DEFAULT_CATEGORIES = [
    "bar",
    "cafe",
    "restaurant",
    "pub",
    "fast_food",
    "biergarten",
    "bakery",
    "nightclub",
]
CITY_ALIASES = {
    "munich": "München",
    "muenchen": "München",
}
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "SparkOccupancyAPI/0.1 (local venue import script)",
}
EXCLUDED_NAME_TOKENS = {
    "casino",
    "sportcasino",
    "sportsbet",
    "sportsbook",
    "bookmaker",
    "betting",
    "gambling",
}
EXCLUDED_TAG_PAIRS = {
    ("amenity", "casino"),
    ("amenity", "gambling"),
    ("shop", "bookmaker"),
}


def parse_categories(raw: str) -> list[str]:
    return [
        normalize_category(category) for category in raw.split(",") if category.strip()
    ]


def overpass_city_name(city: str) -> str:
    return CITY_ALIASES.get(city.strip().lower(), city.strip())


def build_query(city: str, categories: list[str], timeout: int) -> str:
    regex = "|".join(sorted(set(categories)))
    city_name = overpass_city_name(city)
    return f"""
    [out:json][timeout:{timeout}];
    area["boundary"="administrative"]["name"="{city_name}"]->.searchArea;
    (
      node["amenity"~"^({regex})$"](area.searchArea);
      way["amenity"~"^({regex})$"](area.searchArea);
      relation["amenity"~"^({regex})$"](area.searchArea);
      node["shop"~"^({regex})$"](area.searchArea);
      way["shop"~"^({regex})$"](area.searchArea);
      relation["shop"~"^({regex})$"](area.searchArea);
    );
    out center tags;
    """


def address_from_tags(tags: dict[str, str]) -> str | None:
    street = tags.get("addr:street")
    house_number = tags.get("addr:housenumber")
    postcode = tags.get("addr:postcode")
    city = tags.get("addr:city")
    first_line = " ".join(part for part in [street, house_number] if part)
    second_line = " ".join(part for part in [postcode, city] if part)
    address = ", ".join(part for part in [first_line, second_line] if part)
    return address or None


def element_coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def normalize_element(element: dict[str, Any], city: str) -> dict[str, Any] | None:
    tags = element.get("tags", {})
    coords = element_coordinates(element)
    if not coords:
        return None
    category = normalize_category(tags.get("amenity") or tags.get("shop"))
    name = tags.get("name")
    osm_type = element["type"]
    osm_id = str(element["id"])
    return {
        "merchant_id": f"osm_{osm_type}_{osm_id}",
        "osm_type": osm_type,
        "osm_id": osm_id,
        "name": name or f"Unnamed {category} {osm_id}",
        "category": category,
        "lat": coords[0],
        "lon": coords[1],
        "city": city,
        "address": address_from_tags(tags),
        "website": tags.get("website") or tags.get("contact:website"),
        "phone": tags.get("phone") or tags.get("contact:phone"),
        "opening_hours": tags.get("opening_hours"),
        "source": "openstreetmap",
        "raw_tags": tags,
    }


def is_excluded_venue(element: dict[str, Any], venue: dict[str, Any]) -> bool:
    tags = element.get("tags", {})
    for key, value in EXCLUDED_TAG_PAIRS:
        if (tags.get(key) or "").strip().lower() == value:
            return True
    name = str(venue.get("name") or "").lower()
    return any(token in name for token in EXCLUDED_NAME_TOKENS)


def fetch_venues(
    city: str, categories: list[str], include_unnamed: bool, timeout: int
) -> list[dict[str, Any]]:
    query = build_query(city, categories, timeout)
    response = requests.post(
        OVERPASS_URL,
        data={"data": query.encode("utf-8")},
        headers=OVERPASS_HEADERS,
        timeout=timeout + 10,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        message = response.text.strip().replace("\n", " ")
        raise RuntimeError(
            f"Overpass request failed with HTTP {response.status_code}: {message[:500]}"
        ) from exc
    payload = response.json()
    venues = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        if not include_unnamed and not tags.get("name"):
            continue
        venue = normalize_element(element, overpass_city_name(city))
        if venue and not is_excluded_venue(element, venue):
            venues.append(venue)
    venues.sort(key=lambda item: (item["name"].lower(), item["merchant_id"]))
    return venues


def limit_venues(
    venues: list[dict[str, Any]], limit: int | None, seed: int | None
) -> list[dict[str, Any]]:
    if not limit or limit >= len(venues):
        return venues
    if seed is None:
        return venues[:limit]
    rng = random.Random(seed)
    sampled = rng.sample(venues, limit)
    return sorted(sampled, key=lambda item: (item["name"].lower(), item["merchant_id"]))


def write_json(path: Path, venues: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(venues, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, venues: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "merchant_id",
        "osm_type",
        "osm_id",
        "name",
        "category",
        "lat",
        "lon",
        "city",
        "address",
        "website",
        "phone",
        "opening_hours",
        "source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for venue in venues:
            writer.writerow({field: venue.get(field) for field in fields})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch city venues from OpenStreetMap via Overpass."
    )
    parser.add_argument("--city", default="München", help="Administrative city name.")
    parser.add_argument("--categories", default=",".join(DEFAULT_CATEGORIES))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default="resources/mock_venues_munich.json")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--include-unnamed", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    categories = parse_categories(args.categories)
    venues = fetch_venues(args.city, categories, args.include_unnamed, args.timeout)
    limited = limit_venues(venues, None if args.limit == 0 else args.limit, args.seed)
    output = Path(args.output)

    if args.format == "json":
        write_json(output, limited)
    else:
        write_csv(output, limited)

    if args.db_path:
        upsert_venues(args.db_path, limited)

    print(f"Fetched {len(venues)} venues, wrote {len(limited)} to {output}")
    if args.db_path:
        print(f"Imported {len(limited)} venues into {args.db_path}")


if __name__ == "__main__":
    main()

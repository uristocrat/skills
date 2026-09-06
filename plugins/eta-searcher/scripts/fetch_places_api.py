#!/usr/bin/env python3
"""Fetch local business listings from Google Places API (New).

Uses POST https://places.googleapis.com/v1/places:searchText with the
documented field mask. Paginates via pageToken. Dedupes by place id.
Emits CSV with header: name,category,address,phone,website,rating,reviews,source_url
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from typing import Any, Iterable

try:
    import requests
except ImportError:
    sys.stderr.write(
        "The 'requests' package is required. Install with: pip install -r scripts/requirements.txt\n"
    )
    sys.exit(2)


PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = (
    "places.id,places.displayName,places.primaryType,places.types,"
    "places.formattedAddress,places.internationalPhoneNumber,"
    "places.websiteUri,places.rating,places.userRatingCount,"
    "nextPageToken"
)
CSV_HEADER = [
    "name",
    "category",
    "address",
    "phone",
    "website",
    "rating",
    "reviews",
    "source_url",
]
PAGE_SIZE = 20
HARD_CEILING = 100
COST_PROMPT_THRESHOLD = 50


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fetch_places_api.py",
        description=(
            "Fetch local business listings from Google Places API (New). "
            "Requires GOOGLE_MAPS_API_KEY in the environment."
        ),
    )
    p.add_argument("--industry", required=True, help="Industry term, e.g. 'dentists'")
    p.add_argument("--region", required=True, help="City + state or metro, e.g. 'Austin, TX'")
    p.add_argument(
        "--count",
        type=int,
        default=40,
        help="Target number of leads. Default 40. Hard ceiling 100.",
    )
    p.add_argument("--out", default="leads.csv", help="Output CSV path. Default leads.csv")
    p.add_argument(
        "--yes-cost",
        action="store_true",
        help="Skip the interactive cost confirmation for counts above 50.",
    )
    return p


def confirm_cost(count: int) -> bool:
    requests_needed = (count + PAGE_SIZE - 1) // PAGE_SIZE
    sys.stderr.write(
        f"Cost estimate: about {requests_needed} Text Search request(s) for {count} rows.\n"
        f"Places API (New) Text Search is billed per request. See references/places_api_setup.md.\n"
        f"Proceed? [y/N]: "
    )
    sys.stderr.flush()
    try:
        answer = input().strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def fetch_pages(
    api_key: str, industry: str, region: str, target: int
) -> tuple[list[dict[str, Any]], str | None]:
    """Return (places, error_message). On success error_message is None."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    query = f"{industry} in {region}"
    body: dict[str, Any] = {"textQuery": query, "pageSize": PAGE_SIZE}
    seen_ids: set[str] = set()
    out: list[dict[str, Any]] = []
    page_token: str | None = None

    while len(out) < target:
        if page_token:
            body["pageToken"] = page_token
        else:
            body.pop("pageToken", None)

        try:
            resp = requests.post(
                PLACES_TEXT_SEARCH_URL, headers=headers, data=json.dumps(body), timeout=30
            )
        except requests.RequestException as exc:
            return out, f"Network error talking to Google Places API: {exc}"

        if resp.status_code == 403:
            text = resp.text or ""
            if "billing" in text.lower():
                return (
                    out,
                    "Google Places API billing is not enabled on this Cloud project. "
                    "See references/places_api_setup.md.",
                )
            return out, f"Google Places API returned 403. Body: {text[:300]}"

        if resp.status_code == 429:
            return (
                out,
                "Google Places API quota exceeded for the current period. "
                "Either wait for reset or raise the quota in Google Cloud Console.",
            )

        if resp.status_code != 200:
            text = resp.text or ""
            if "API_KEY_INVALID" in text:
                return (
                    out,
                    "GOOGLE_MAPS_API_KEY is invalid or restricted. "
                    "Check the key in Google Cloud Console.",
                )
            if "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
                return (
                    out,
                    "Google Places API quota exceeded for the current period. "
                    "Either wait for reset or raise the quota in Google Cloud Console.",
                )
            return (
                out,
                f"Google Places API returned HTTP {resp.status_code}. Body: {text[:300]}",
            )

        try:
            data = resp.json()
        except ValueError:
            return out, "Google Places API returned a non-JSON body."

        places: Iterable[dict[str, Any]] = data.get("places", []) or []
        for place in places:
            pid = place.get("id")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            out.append(place)
            if len(out) >= target:
                break

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        # Google requires a brief delay before a pageToken becomes active.
        time.sleep(2)

    return out, None


def place_to_row(place: dict[str, Any]) -> dict[str, str]:
    name = (place.get("displayName") or {}).get("text") or ""
    category = place.get("primaryType") or ""
    address = place.get("formattedAddress") or ""
    phone = place.get("internationalPhoneNumber") or ""
    website = place.get("websiteUri") or ""
    rating = place.get("rating")
    reviews = place.get("userRatingCount")
    pid = place.get("id") or ""
    source_url = f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else ""

    return {
        "name": name,
        "category": category,
        "address": address,
        "phone": phone,
        "website": website,
        "rating": "" if rating is None else f"{rating}",
        "reviews": "" if reviews is None else f"{reviews}",
        "source_url": source_url,
    }


def write_csv(path: str, rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_summary(rows: list[dict[str, str]], industry: str, region: str, out_path: str) -> None:
    total = len(rows)
    with_phone = sum(1 for r in rows if r["phone"])
    with_website = sum(1 for r in rows if r["website"])

    sys.stdout.write(f"\nLead list: {industry} in {region}\n")
    sys.stdout.write(f"- Total leads: {total}\n")
    if total:
        sys.stdout.write(
            f"- With phone: {with_phone} ({with_phone * 100 // total}%)\n"
            f"- With website: {with_website} ({with_website * 100 // total}%)\n"
        )
    else:
        sys.stdout.write("- With phone: 0\n- With website: 0\n")
    sys.stdout.write("- Source: Google Places API (New)\n")
    sys.stdout.write(f"- CSV: {out_path}\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.count <= 0:
        sys.stderr.write("--count must be a positive integer.\n")
        return 2

    if args.count > HARD_CEILING:
        sys.stderr.write(
            f"--count is above the hard ceiling of {HARD_CEILING}. "
            "Split the request by sub-region (zip, neighborhood, or adjacent city) and run again.\n"
        )
        return 2

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        sys.stderr.write(
            "GOOGLE_MAPS_API_KEY is not set. The Google Places API (New) is the preferred path. "
            "See references/places_api_setup.md for setup. "
            "A Playwright scrape fallback exists at scripts/scrape_listings.py, "
            "but it is against Google's Terms of Service and requires explicit --yes-tos confirmation.\n"
        )
        return 2

    if args.count > COST_PROMPT_THRESHOLD and not args.yes_cost:
        if not confirm_cost(args.count):
            sys.stderr.write("Aborted before any API call was made.\n")
            return 1

    places, err = fetch_pages(api_key, args.industry, args.region, args.count)
    if err:
        sys.stderr.write(err + "\n")
        # Still write whatever we got, so partial progress isn't lost.
        rows = [place_to_row(p) for p in places]
        write_csv(args.out, rows)
        print_summary(rows, args.industry, args.region, args.out)
        return 1

    rows = [place_to_row(p) for p in places]
    write_csv(args.out, rows)

    if not rows:
        sys.stderr.write(
            "Zero results. Try a broader industry term or a wider region. "
            "No traceback, just nothing to return.\n"
        )

    print_summary(rows, args.industry, args.region, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

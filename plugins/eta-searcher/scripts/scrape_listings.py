#!/usr/bin/env python3
"""Playwright + Chromium fallback scraper for Google Maps listings.

This is a fallback, not the recommended path. Scraping Google Maps is
against Google's Terms of Service. Requires explicit --yes-tos to run.

Emits the same CSV schema as fetch_places_api.py:
  name,category,address,phone,website,rating,reviews,source_url
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from urllib.parse import quote_plus

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
DEFAULT_CAP = 40
HARD_CEILING = 100
REQUEST_DELAY_SECONDS = 1.5

TOS_WARNING = (
    "WARNING: scraping Google Maps is against Google's Terms of Service. "
    "The Google Places API (New) is the preferred path. "
    "See references/places_api_setup.md."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scrape_listings.py",
        description=(
            "Fallback scraper for Google Maps listings using Playwright + Chromium. "
            "Against Google's Terms of Service. Requires --yes-tos."
        ),
    )
    p.add_argument("--industry", required=True, help="Industry term, e.g. 'dentists'")
    p.add_argument("--region", required=True, help="City + state or metro, e.g. 'Austin, TX'")
    p.add_argument(
        "--count",
        type=int,
        default=DEFAULT_CAP,
        help=f"Target number of leads. Default {DEFAULT_CAP}. Hard ceiling {HARD_CEILING}.",
    )
    p.add_argument("--out", default="leads.csv", help="Output CSV path. Default leads.csv")
    p.add_argument(
        "--yes-tos",
        action="store_true",
        help=(
            "Explicit acknowledgment that scraping Google Maps violates Google's ToS. "
            "Without this flag, the script refuses to run."
        ),
    )
    p.add_argument(
        "--headful",
        action="store_true",
        help="Run Chromium in headful mode (useful for debugging).",
    )
    return p


def search_url(industry: str, region: str) -> str:
    return f"https://www.google.com/maps/search/{quote_plus(industry + ' in ' + region)}"


def parse_rating_reviews(text: str) -> tuple[str, str]:
    """Parse strings like '4.5(123)' or '4.5 stars 123 reviews'."""
    if not text:
        return "", ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*\(?\s*([\d,]+)\s*\)?", text)
    if m:
        rating = m.group(1)
        reviews = m.group(2).replace(",", "")
        return rating, reviews
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        return m.group(1), ""
    return "", ""


def scrape(
    industry: str,
    region: str,
    target: int,
    headful: bool,
) -> tuple[list[dict[str, str]], str | None]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return (
            [],
            "Playwright is not installed. Install with: "
            "pip install -r scripts/requirements.txt && python -m playwright install chromium",
        )

    url = search_url(industry, region)
    results: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=not headful)
        except Exception as exc:
            return [], f"Could not launch Chromium. Run: python -m playwright install chromium. {exc}"

        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=45000)
        except PWTimeout:
            browser.close()
            return [], "Timed out loading Google Maps."

        # Consent interstitial dismissal.
        for selector in (
            'button[aria-label*="Accept" i]',
            'form[action*="consent"] button',
        ):
            try:
                el = page.locator(selector).first
                if el and el.is_visible(timeout=2000):
                    el.click(timeout=2000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    break
            except Exception:
                continue

        # Confirm the results feed is visible.
        try:
            page.wait_for_selector('[role="feed"]', timeout=15000)
        except PWTimeout:
            browser.close()
            if "consent" in page.url.lower():
                return [], "Google consent page blocked the scrape. Try the API path."
            return [], "Could not find Google Maps results feed."

        feed = page.locator('[role="feed"]').first
        last_count = -1
        stagnant_rounds = 0

        while len(results) < target and stagnant_rounds < 4:
            cards = feed.locator('a[href*="/maps/place/"]')
            count = cards.count()

            for i in range(count):
                if len(results) >= target:
                    break
                card = cards.nth(i)
                try:
                    name = (card.get_attribute("aria-label") or "").strip()
                    href = card.get_attribute("href") or ""
                except Exception:
                    continue
                if not name or not href:
                    continue

                try:
                    card.click(timeout=5000)
                    page.wait_for_timeout(int(REQUEST_DELAY_SECONDS * 1000))
                except Exception:
                    continue

                detail: dict[str, str] = {
                    "name": name,
                    "category": "",
                    "address": "",
                    "phone": "",
                    "website": "",
                    "rating": "",
                    "reviews": "",
                    "source_url": href,
                }

                try:
                    cat_el = page.locator('button[jsaction*="category"]').first
                    if cat_el and cat_el.is_visible(timeout=1000):
                        detail["category"] = (cat_el.inner_text() or "").strip()
                except Exception:
                    # Category is optional; leave it blank and keep scraping.
                    pass

                try:
                    addr_el = page.locator('button[data-item-id="address"]').first
                    if addr_el and addr_el.is_visible(timeout=1000):
                        detail["address"] = (
                            addr_el.get_attribute("aria-label") or addr_el.inner_text() or ""
                        ).replace("Address:", "").strip()
                except Exception:
                    # Address is optional; leave it blank and keep scraping.
                    pass

                try:
                    phone_el = page.locator('button[data-item-id^="phone:"]').first
                    if phone_el and phone_el.is_visible(timeout=1000):
                        detail["phone"] = (
                            phone_el.get_attribute("aria-label") or phone_el.inner_text() or ""
                        ).replace("Phone:", "").strip()
                except Exception:
                    # Phone is optional; leave it blank for this listing and keep scraping.
                    pass

                try:
                    site_el = page.locator('a[data-item-id="authority"]').first
                    if site_el and site_el.is_visible(timeout=1000):
                        detail["website"] = (site_el.get_attribute("href") or "").strip()
                except Exception:
                    # Website is optional; leave it blank and keep scraping.
                    pass

                try:
                    rating_label = (
                        page.locator('div[role="img"][aria-label*="star" i]')
                        .first.get_attribute("aria-label")
                    )
                    if rating_label:
                        detail["rating"], detail["reviews"] = parse_rating_reviews(rating_label)
                except Exception:
                    # Rating/reviews are optional; leave them blank and keep scraping.
                    pass

                dedupe_key = (detail["name"].lower(), detail["address"].lower())
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                results.append(detail)

            # Scroll the feed to load more results.
            try:
                feed.evaluate("(el) => el.scrollBy(0, el.clientHeight)")
                page.wait_for_timeout(int(REQUEST_DELAY_SECONDS * 1000))
            except Exception:
                break

            new_count = cards.count()
            if new_count <= last_count:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
                last_count = new_count

        browser.close()

    return results, None


def write_csv(path: str, rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in rows:
            # Ensure every key exists.
            full = {k: row.get(k, "") for k in CSV_HEADER}
            writer.writerow(full)


def print_summary(rows: list[dict[str, str]], industry: str, region: str, out_path: str) -> None:
    total = len(rows)
    with_phone = sum(1 for r in rows if r.get("phone"))
    with_website = sum(1 for r in rows if r.get("website"))
    sys.stdout.write(f"\nLead list: {industry} in {region}\n")
    sys.stdout.write(f"- Total leads: {total}\n")
    if total:
        sys.stdout.write(
            f"- With phone: {with_phone} ({with_phone * 100 // total}%)\n"
            f"- With website: {with_website} ({with_website * 100 // total}%)\n"
        )
    else:
        sys.stdout.write("- With phone: 0\n- With website: 0\n")
    sys.stdout.write("- Source: Google Maps scrape (ToS opt-in)\n")
    sys.stdout.write(f"- CSV: {out_path}\n")


def main(argv: list[str] | None = None) -> int:
    # ToS warning to stderr on every invocation.
    sys.stderr.write(TOS_WARNING + "\n")

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.yes_tos:
        sys.stderr.write(
            "Refusing to run. Pass --yes-tos to acknowledge that scraping Google Maps "
            "violates Google's Terms of Service. The Google Places API (New) is the preferred path.\n"
        )
        return 2

    if args.count <= 0:
        sys.stderr.write("--count must be a positive integer.\n")
        return 2

    if args.count > HARD_CEILING:
        sys.stderr.write(
            f"--count is above the hard ceiling of {HARD_CEILING}. "
            "Split the request by sub-region (zip, neighborhood, or adjacent city) and run again.\n"
        )
        return 2

    rows, err = scrape(args.industry, args.region, args.count, args.headful)
    if err:
        sys.stderr.write(err + "\n")
        # Still write partial output.
        write_csv(args.out, rows)
        print_summary(rows, args.industry, args.region, args.out)
        return 1

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

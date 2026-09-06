# Google Places API (New) setup

This is the preferred path for Local Lead Prospector. It is the official, ToS-clean way to pull Google Maps listing data.

## One-time setup

1. Go to Google Cloud Console at https://console.cloud.google.com.
2. Create a new project, or pick an existing one you are happy to bill against.
3. Enable the **Places API (New)** for that project. The legacy "Places API" is a separate product. You need the (New) one.
4. Enable billing on the project. Without billing, every request returns HTTP 403 with a body that mentions billing.
5. Create an API key under **APIs & Services > Credentials**. Restrict it to the Places API (New) only. Optionally restrict by IP if you only run from one machine.
6. Export the key:

```
export GOOGLE_MAPS_API_KEY="YOUR_KEY_HERE"
```

Add that line to your shell profile so it persists.

## Pricing notes

Places API (New) Text Search is billed per request, not per result. Each request can return up to 20 results, so a 100-row pull is about 5 paginated requests. Google publishes the current SKU prices at https://mapsplatform.google.com/pricing. There is a monthly free tier that covers small experiments. The skill shows a cost estimate before any pull above 50 rows.

## Field mask

The fetch script requests this field mask, which controls cost (more fields equals a higher SKU tier):

```
places.id,places.displayName,places.primaryType,places.types,places.formattedAddress,places.internationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount
```

This stays in the "Pro" tier, not "Enterprise". Do not add `places.reviews` or `places.photos` casually. Those bump the tier.

## Verification

After setting the key, run:

```
python scripts/fetch_places_api.py --industry "coffee shops" --region "Austin, TX" --count 10 --out /tmp/check.csv
```

If you see a CSV with 10 rows and a non-zero number of phone numbers and websites, the setup is working.

## Common failure modes

- **HTTP 403 with "billing" in the body.** Billing is not enabled. Fix in Cloud Console > Billing.
- **`API_KEY_INVALID`.** Key is wrong, restricted to a different API, or restricted to a different IP. Check Credentials.
- **Quota exceeded.** You hit the per-minute or per-day quota. Wait or raise it in Cloud Console > Quotas.
- **Zero results.** The query string was too narrow. Try a broader industry term or a wider region.

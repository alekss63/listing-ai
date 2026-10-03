# ListingAI - eBay Listing Assistant

Turns product photos into eBay listings: Claude vision reads the photos (tags,
measurements, condition), local Ollama writes the listing copy at $0 per draft,
and a review dashboard pushes the result to eBay.

## Status (2026-10-03)

**Working end to end on the production eBay account.** First two products
(05277 Cremieux shirt, 06522 Oakley tee) went photos → AI draft → Seller Hub
draft → revised → **published live**.

| Piece | State |
|---|---|
| Photo discovery, classification, OCR, measurements (Claude) | Working |
| Draft generation (Ollama `qwen2.5-coder:14b`, ~20 s/draft) | Working - output needs review (see Known issues) |
| eBay auth (OAuth + automatic refresh, ~18 months) | Working |
| Photo upload to eBay Picture Services | Working |
| Push as unpublished offer + Publish Live (Inventory API) | Working, one click each - not yet used for a real listing |
| Seller Hub Drafts file (Reports → Uploads) | Working - this is how the first 2 listings were made |
| eBay search (Browse API) | Working |

## Running the dashboard

```bash
.venv/bin/uvicorn backend.app.main:app --reload --reload-dir backend
```

Then open http://127.0.0.1:8000. Ollama must be running for AI drafts.
`--reload-dir backend` keeps the reloader from watching `.venv`, `Pictures`
and `storage` (over 1 GB), which otherwise pins a CPU core.

## One-time eBay setup (done for this account)

1. `.venv/bin/python scripts/ebay_oauth.py` - sign in with the real seller
   account and paste back the **full** address-bar URL within ~5 minutes. Saves
   `EBAY_USER_TOKEN` and `EBAY_REFRESH_TOKEN` to `.env`; the backend renews
   access tokens itself after that. `EBAY_DOMAIN` picks sandbox vs production,
   and `EBAY_APP_ID`, `EBAY_CERT_ID` and `EBAY_RUNAME` must all come from that
   same keyset.
2. `.venv/bin/python scripts/create_location.py` - asks for your ship-from
   city, state and ZIP. Required to publish.
3. Business policy IDs are hard-coded at the top of
   `backend/app/services/ebay/draft_pusher.py` (shipping "Post", payment
   "Payments1", returns "Returns Light") - verified against the account.

## Listing a product

Dashboard → **eBay Drafts** → click a product:

1. **Generate with AI**, then review title (80-char limit), price, condition,
   specifics and description, and **Save**.
2. Pick **one** route per product - doing both creates duplicate listings:
   - **API route (fewest clicks):** **Push to eBay** (uploads photos, creates an
     unpublished offer buyers can't see) → **Publish Live**. eBay validates on
     publish and the dashboard shows exactly what's missing. Pushing again
     after publishing revises the live listing.
   - **Seller Hub route:** back on the list, **Download Seller Hub Drafts File**,
     then Seller Hub → Reports → Uploads → **Upload template** → type
     **Create drafts**. Drafts appear at https://www.ebay.com/sh/lst/drafts to
     finish and list there. Don't open the file in Excel first, and upload each
     file once.

## Known issues

- **Too much manual work per item.** The Seller Hub route took longer than
  listing by hand: download file → upload → fix in Seller Hub → list. The API
  route is two clicks per item but hasn't been used for a real listing yet.
- **AI drafts get details wrong**, so every draft needs a careful review. Seen so
  far: title "Short Sleeve" vs specifics "Long Sleeve" (05277); material "Cotton
  Blend" while the description says 50/50 cotton/poly, and colour "Red" for a
  multicolour shirt (06522); plain-text descriptions without measurements.
- **Products listed through Seller Hub are managed there.** 05277 and 06522 are
  marked `listed_via: seller_hub` in their manifests, and the dashboard blocks
  Push and Publish for them, since either would create a duplicate. (Their
  leftover test API offers were deleted on 2026-10-03.)
- `Seller Hub Drafts` must be uploaded by hand: the Sell Feed API (FX_LISTING)
  rejects the `Draft` action with `BAF.Error.5 Unable to find Task Action Id`.

## Next steps (to cut the manual work)

1. List the next products through the **API route** and see if it holds up.
2. Better drafts: give Ollama the manifest's measurements and Claude's
   item specifics as hard facts, with a rule against contradicting them; HTML
   description template with measurements.
3. Check the category's required item specifics (Taxonomy API
   `get_item_aspects_for_category`) at push time, so gaps show before publishing.
4. Batch buttons: "Generate all", "Push all reviewed", "Publish all pushed".
5. Show listing state from eBay itself rather than only local files.

## Lessons learned (eBay API gotchas)

- User access tokens expire after ~2 hours, so use the refresh token.
- The OAuth code in the address bar is URL-encoded and single-use, expiring in ~5 minutes.
- Sign in as the **selling** account, not the developer account (earlier 403s).
  A private/incognito window helps.
- Sell APIs need `Content-Language: en-US` and `X-EBAY-C-MARKETPLACE-ID: EBAY_US`.
- The offer price goes under `pricingSummary.price`. `"status": "DRAFT"` isn't a real field.
- Conditions are enums (`NEW`, `NEW_OTHER`, ...) and aspect names are
  capitalised (`Brand`).
- The location list comes back under `locations`, not `merchantLocations`.
- Inventory API offers never appear in Seller Hub Drafts.
- Photos go to the Media API on `apim.ebay.com`. Unused uploads expire.
- A Seller Hub upload file must start with the template's exact `#INFO` line.

## Development

```bash
.venv/bin/python -m pytest -q      # 53 tests, no network or AI calls
.venv/bin/ruff check . && .venv/bin/black --check backend scripts
```

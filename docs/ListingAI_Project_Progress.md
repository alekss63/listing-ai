# ListingAI Project Progress

## 🎯 Project Goal
Cost-effective, automated eBay draft creation using local AI (Ollama), ready for manual approval and listing, with $0 API costs for AI generation.

## ✅ Major Milestones Achieved

### 1. eBay Browse API Search (Working)
- Successfully integrated `GET /api/products/search` endpoint.
- Resolved 403 "Access Denied" errors by adding required `X-EBAY-C-MARKETPLACE-ID` header and removing `Content-Type` from GET requests.
- Successfully parsing eBay JSON responses into Pydantic `ProductSearchResponse` models.

### 2. Local AI Draft Generation (Working)
- Integrated local Ollama instance (`qwen2.5-coder:14b`) for $0 cost AI generation.
- Created `POST /api/drafts/generate/{sku}` endpoint.
- AI successfully reads local `manifest.json` and outputs strict, validated JSON drafts (Title, Description, Price, Condition, Item Specifics, AI Notes).
- Drafts are safely saved to the local `/drafts` folder for human review.

### 3. eBay Authentication Breakthrough (Solved)
- **The Problem:** Persistent 403 "Insufficient permissions" and 404 "Resource not found" errors on Sell APIs.
- **The Root Cause:** The Developer Account token was being used instead of the main 14-year Selling Account token.
- **The Solution:** Used the "Incognito Trick" to force the Developer App to request OAuth permissions from the actual Production Selling Account. 
- **Verification:** Standalone Python scripts confirm the token now has valid `sell.account` and `sell.inventory` scopes (HTTP 200).

### 4. Draft Pusher Service (Code Complete, Pending Route Registration)
- Created `backend/app/services/ebay/draft_pusher.py`.
- Implements the 2-step eBay Sell API flow: 
  1. `PUT /sell/inventory/v1/inventory_item/{sku}` (Creates the product data).
  2. `POST /sell/inventory/v1/offer` (Creates the listing with `"status": "DRAFT"`).
- Added critical headers: `Content-Language: en-US` and `marketplaceId: "EBAY_US"` in the payload.

## 🚧 Current Blocker (To be resolved next session)
- **FastAPI Route Registration Ghost:** The `drafts_router` is correctly defined in `backend/app/api/drafts.py` and imports successfully in isolation, but the live `uvicorn` server is not registering the `/api/drafts/...` routes. 
- **Next Action:** Investigate Python caching, `__init__.py` shadowing, or circular imports preventing `app.include_router(drafts_router)` from executing properly in `main.py`.

## 📁 Key Files Modified/Created
- `backend/app/api/routes.py` (eBay search endpoint)
- `backend/app/api/drafts.py` (Draft generation and push endpoints)
- `backend/app/services/ai/listing_generator.py` (Ollama integration)
- `backend/app/services/ebay/draft_pusher.py` (eBay Sell API integration)
- `backend/app/schemas.py` (Added `ListingDraft` and `ItemSpecifics` models)
- `.env` (Updated with Production `EBAY_DOMAIN` and valid Production `EBAY_USER_TOKEN`)
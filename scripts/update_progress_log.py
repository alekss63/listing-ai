from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROGRESS_FILE = PROJECT_ROOT / "Docs" / "ListingAI_Project_Progress.md"
PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

CONTENT = """# ListingAI Project Progress Log

## Project Identity
- **Project name:** ListingAI
- **GitHub repository:** https://github.com/alekss63/listing-ai

## Goal
Build a production-quality AI marketplace listing automation system.
- **Initial marketplace:** eBay Sandbox
- **AI engine:** Anthropic Claude Vision
- **Future possibilities:** Etsy, Shopify, Facebook Marketplace, Poshmark

## Architecture Decision
**Core workflow:**
Raw Photos (Inbox) ↓ Smart AI Grouping ↓ Discovery Engine ↓ Image Classification (Chunked) ↓ OCR ↓ Measurement Extraction ↓ Claude Listing Generation ↓ Persistent Storage ↓ Archive (Processed/) ↓ Human Review API

## Current Development Stage
### Sprint 7: Smart Grouping, Prompt Refinement & Routing (COMPLETE)
**Goal:** Allow users to drop loose photos into the `Pictures/` inbox and have the AI automatically group them by physical product.
**Status:** Complete.
- Added `smart_grouper.py` to analyze loose photos and group them by item.
- Added `garment_type` extraction to OCR pipeline.
- Implemented automatic archiving of processed photos to `Processed/` folder.
- Added chunking (processing images 2 at a time) and auto-retry logic to bypass macOS SSL payload limits.

## Folder Architecture
```text
listing-ai/
├── backend/app/services/
│   ├── ai/         (vision_client, photo_classifier, listing_generator)
│   ├── discovery/  (image_scanner, smart_grouper, manifest_builder, storage)
│   ├── ocr/        (tag_extractor)
│   └── measurements/ (measurement_extractor)
├── Pictures/       <-- INBOX (Drop raw loose photos here)
├── Processed/      <-- ARCHIVE (Pipeline moves photos here)
├── storage/products/ <-- DATA (manifest.json)
└── Docs/           <-- Project documentation
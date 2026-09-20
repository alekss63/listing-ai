# ListingAI Project Progress Log

## Project Identity
- **Project name:** ListingAI
- **GitHub repository:** https://github.com/alekss63/listing-ai

## Goal
Build a production-quality AI marketplace listing automation system.
- **Initial marketplace:** eBay Sandbox
- **AI engine:** Anthropic Claude Vision

## Architecture Decision
**Core workflow:**
Raw Photos (Inbox) ↓ Smart AI Grouping ↓ Image Classification (Chunked) ↓ OCR (Prioritizing Bag Stickers) ↓ Measurement Extraction ↓ Condition Assessment ↓ Claude Listing Generation ↓ Persistent Storage ↓ Archive (Processed/) ↓ Human Review Web API

## Current Development Stage
### Sprint 8: Human Review API & Refinements (COMPLETE)
**Goal:** Build a local web dashboard to visually review/edit AI drafts, and refine AI prompts for real-world reseller workflows.
**Status:** Complete.
- Built a FastAPI web server running on `http://127.0.0.1:8000`.
- Created an interactive frontend (`static/index.html`) with a "Live Visual Preview" (contenteditable HTML) for easy description editing.
- Added `condition_assessor.py` to automatically grade items as "New without tags", "Pre-owned", or "New with imperfections" based on visual defects.
- Refined OCR pipeline to prioritize reading SKU stickers on plastic bags (usually the first photo) before reading interior garment tags.
- Implemented smart fallback SKUs (Brand-Color-Type) when no physical sticker is found.

## Folder Architecture
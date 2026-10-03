"""Shared test fixtures.

build_manifest drives the whole AI pipeline: photo classification, tag OCR,
measurement extraction, condition assessment and listing generation. Every one
of those calls the Anthropic API and reads real image files, so tests that
exercise discovery end to end would otherwise need network access and fixture
photographs on disk.

The autouse fixture below replaces that boundary with empty results, leaving
the surrounding logic - grouping, SKU fallback, manifest assembly and
serialization - running for real. A test that wants different AI output can
monkeypatch these names again itself.
"""

import pytest

from backend.app.services.discovery import manifest_builder


@pytest.fixture(autouse=True)
def stub_ai_pipeline(monkeypatch):
    monkeypatch.setattr(manifest_builder, "classify_photos", lambda *a, **k: {})
    monkeypatch.setattr(manifest_builder, "extract_tag_data", lambda *a, **k: {})
    monkeypatch.setattr(manifest_builder, "extract_measurements", lambda *a, **k: {})
    monkeypatch.setattr(manifest_builder, "assess_condition", lambda *a, **k: {})
    monkeypatch.setattr(manifest_builder, "generate_listing", lambda *a, **k: {})

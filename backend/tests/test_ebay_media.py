import asyncio
import io

import httpx
from PIL import Image

from backend.app.services.ebay import media

MANIFEST = {
    "photos": {
        "sku_photo": "sticker.jpg",
        "tag_photos": ["tag.jpg"],
        "measurement_photos": ["measure.jpg"],
        "defect_photos": [],
        "front_photo": "front.jpg",
        "back_photo": "back.jpg",
        "detail_photos": [],
    },
    "raw_images": [
        "sticker.jpg",
        "tag.jpg",
        "front.jpg",
        "extra.jpg",
        "back.jpg",
        "measure.jpg",
    ],
}


def test_listing_photos_lead_with_front_and_never_include_sku_sticker():
    assert media.listing_photo_filenames(MANIFEST) == [
        "front.jpg",
        "back.jpg",
        "tag.jpg",
        "measure.jpg",
        "extra.jpg",
    ]


def test_listing_photos_capped_at_ebay_limit():
    manifest = {"raw_images": [f"{i}.jpg" for i in range(30)]}
    assert len(media.listing_photo_filenames(manifest)) == media.MAX_LISTING_PHOTOS


def test_prepare_image_shrinks_phone_photos_to_jpeg(tmp_path):
    path = tmp_path / "big.png"
    Image.new("RGBA", (4284, 3000)).save(path)

    with Image.open(io.BytesIO(media.prepare_image(path))) as out:
        assert out.format == "JPEG"
        assert max(out.size) == media.MAX_DIMENSION
        assert out.size == (1600, 1120)  # aspect ratio kept


def test_ensure_listing_images_reuses_fresh_uploads(tmp_path, monkeypatch):
    for name in ("front.jpg", "back.jpg"):
        Image.new("RGB", (800, 800)).save(tmp_path / name)
    monkeypatch.setattr(media, "get_headers", lambda: {"Content-Type": "x"})

    uploads = []

    def handler(request: httpx.Request) -> httpx.Response:
        # multipart must carry its own boundary, not our JSON content type
        assert request.headers["Content-Type"].startswith("multipart/form-data")
        uploads.append(request)
        return httpx.Response(
            201,
            json={
                "imageUrl": f"https://i.ebayimg.com/{len(uploads)}.jpg",
                "expirationDate": "2999-01-01T00:00:00.000Z",
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        media.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler)),
    )
    cache = {
        # Still valid -> reused
        "front.jpg": {
            "imageUrl": "https://i.ebayimg.com/cached.jpg",
            "expirationDate": "2999-01-01T00:00:00.000Z",
        },
        # Expired -> re-uploaded
        "back.jpg": {
            "imageUrl": "https://i.ebayimg.com/old.jpg",
            "expirationDate": "2000-01-01T00:00:00.000Z",
        },
    }

    urls, new_cache = asyncio.run(
        media.ensure_listing_images(
            tmp_path, ["front.jpg", "back.jpg", "missing.jpg"], cache
        )
    )

    assert urls == ["https://i.ebayimg.com/cached.jpg", "https://i.ebayimg.com/1.jpg"]
    assert len(uploads) == 1
    assert new_cache["back.jpg"]["imageUrl"] == "https://i.ebayimg.com/1.jpg"


def test_media_api_uses_apim_host():
    assert "://apim." in media.UPLOAD_URL

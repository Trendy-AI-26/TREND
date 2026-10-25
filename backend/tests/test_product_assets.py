import io
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

from app.routers.product_assets import upload_product_asset
from tests.test_avatar_upload import USER
import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers
from fastapi import HTTPException

from app.config import settings
from app.models.generation import (
    GenerateRequest,
    GenerationBrief,
)


def make_upload_file(
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers=Headers(
            {
                "content-type": content_type,
            }
        ),
    )


VALID_BRIEF = {
    "language": "ar",
    "campaign_goal": "product_launch",
    "campaign_goal_custom": None,
    "content_type": "product_showcase",
    "content_type_custom": None,
    "target_audience": {
        "segments": [
            "small_business_owners",
        ],
        "location": "Amman",
        "age_range": "25_34",
        "gender_focus": "all",
        "details": "Customers interested in the product",
    },
    "core_idea": "Launch a new product in an attractive way",
    "voice_tone": "friendly",
    "voice_tone_custom": None,
    "optional_notes": None,
    "text_to_include": None,
}


VALID_BRIEF_MODEL = GenerationBrief.model_validate(VALID_BRIEF)


BRAND_ID = UUID("11111111-1111-1111-1111-111111111111")
ASSET_FROM_OTHER_BRAND = UUID(
    "33333333-3333-3333-3333-333333333333"
)

# Test that uploading a product asset requires authentication
def test_product_asset_upload_requires_authentication():
    response = client.post(
        "/brands/brand-id/product-assets",
        files={
            "file": (
                "product.png",
                b"fake-image",
                "image/png",
            )
        },
    )

    assert response.status_code == 401

# Test that uploading a product asset rejects invalid image type (مع استخدام monkeypatch أو mock لقاعدة البيانات)
@pytest.mark.asyncio
async def test_product_asset_rejects_invalid_image_type(monkeypatch):
    # محاكاة الاتصال بقاعدة البيانات لكي لا يحدث خطأ الاتصال
    monkeypatch.setattr("app.routers.product_assets._get_owned_brand", lambda b_id, u_id: True)

    file = make_upload_file(
        filename="product.txt",
        content=b"not-an-image",
        content_type="text/plain",
    )

    with pytest.raises(HTTPException) as error:
        await upload_product_asset(
            brand_id=BRAND_ID,
            file=file,
            current_user=USER,
        )

    assert error.value.status_code == 400
    assert (
        error.value.detail["error"]["code"]
        == "INVALID_IMAGE"
    )

@pytest.mark.asyncio
async def test_product_asset_rejects_large_file(monkeypatch):
    monkeypatch.setattr(
        settings,
        "PRODUCT_ASSET_MAX_BYTES",
        10,
    )
    # محاكاة الاتصال بقاعدة البيانات
    monkeypatch.setattr("app.routers.product_assets._get_owned_brand", lambda b_id, u_id: True)

    file = make_upload_file(
        filename="product.png",
        content=b"this content is larger than ten bytes",
        content_type="image/png",
    )

    with pytest.raises(HTTPException) as error:
        await upload_product_asset(
            brand_id=BRAND_ID,
            file=file,
            current_user=USER,
        )

    assert error.value.status_code == 413
    assert (
        error.value.detail["error"]["code"]
        == "FILE_TOO_LARGE"
    )


# Test that GenerateRequest allows product_asset_id to be None
def test_generate_request_allows_no_product_asset():
    request = GenerateRequest(
        brief=VALID_BRIEF_MODEL,
        platform_preset="instagram_post",
        logo_mode="none",
        product_asset_id=None,
    )

    assert request.product_asset_id is None

# Test that GenerateRequest accepts a product_asset_id of type UUID
def test_generate_request_accepts_one_product_asset():
    asset_id = uuid4()

    request = GenerateRequest(
        brief=VALID_BRIEF_MODEL,
        platform_preset="instagram_post",
        logo_mode="none",
        product_asset_id=asset_id,
    )

    assert request.product_asset_id == asset_id
import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app.core.auth import User
from app.routers import me
from starlette.datastructures import Headers


USER = User(
    id="user-123",
    email="user@example.com",
    access_token="test-token",
)

# Test for invalid file type
@pytest.mark.asyncio
async def test_avatar_rejects_invalid_file_type():
    file = make_upload_file(
    filename="avatar.txt",
    content=b"not-an-image",
    content_type="text/plain",
)


    with pytest.raises(HTTPException) as error:
        await me.upload_avatar(
            file=file,
            current_user=USER,
        )

    assert error.value.status_code == 400
    assert error.value.detail["error"]["code"] == "INVALID_AVATAR_TYPE"

# Test for empty file
@pytest.mark.asyncio
async def test_avatar_rejects_empty_file():
    file = make_upload_file(
    filename="avatar.png",
    content=b"",
    content_type="image/png",
)



    with pytest.raises(HTTPException) as error:
        await me.upload_avatar(
            file=file,
            current_user=USER,
        )

    assert error.value.status_code == 400
    assert error.value.detail["error"]["code"] == "EMPTY_AVATAR"

# Test for file size exceeding the limit
@pytest.mark.asyncio
async def test_avatar_rejects_large_file(monkeypatch):
    monkeypatch.setattr(
        me.settings,
        "AVATAR_MAX_BYTES",
        10,
    )

    file = make_upload_file(
    filename="avatar.png",
    content=b"this file is larger than ten bytes",
    content_type="image/png",
)



    with pytest.raises(HTTPException) as error:
        await me.upload_avatar(
            file=file,
            current_user=USER,
        )

    assert error.value.status_code == 413
    assert error.value.detail["error"]["code"] == "AVATAR_TOO_LARGE"

def make_upload_file(
    filename: str,
    content: bytes,
    content_type: str,
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers(
            {
                "content-type": content_type,
            }
        ),
    )

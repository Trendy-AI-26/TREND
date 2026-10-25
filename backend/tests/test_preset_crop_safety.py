"""Characterize current preset cropping and logo bounds without provider calls."""

import io

import pytest
from PIL import Image, ImageChops, ImageDraw

from app.services.postprocess import resize_to_preset
from app.services.presets import PLATFORM_PRESETS
from app.services.providers.openai_image import _openai_size
from app.services.watermark import WATERMARK_MARGIN_PX, apply_logo

EXPECTED_REMOVED_PERCENT = {
    "instagram_post": 0.0,
    "instagram_story": 0.0,
    "instagram_reel_cover": 0.0,
    "facebook_post": 0.0,
    "facebook_cover": 0.12,
    "facebook_story": 0.0,
    "twitter_post": 0.0,
    "twitter_header": 0.0,
    "linkedin_post": 0.48,
    "linkedin_banner": 62.5,
    "tiktok_video_cover": 0.0,
    "youtube_thumbnail": 0.0,
    "youtube_banner": 0.0,
}

BACKGROUND = (16, 16, 16)
TOP = (255, 0, 0)
BOTTOM = (0, 0, 255)
LEFT = (0, 255, 0)
RIGHT = (255, 255, 0)
CENTER = (255, 0, 255)
INNER_MARKERS = (
    (0.125, (96, 0, 192)),
    (0.375, (0, 192, 192)),
    (0.625, (255, 128, 0)),
    (0.875, (255, 255, 255)),
)


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize("preset_id", PLATFORM_PRESETS)
def test_provider_sized_image_is_center_cropped_to_exact_png(preset_id):
    width, height, _label = PLATFORM_PRESETS[preset_id]
    native_width, native_height = map(int, _openai_size(width, height).split("x"))
    source = Image.new("RGB", (native_width, native_height), BACKGROUND)
    draw = ImageDraw.Draw(source)
    band_x, band_y = native_width // 25, native_height // 25
    draw.rectangle((0, 0, native_width - 1, band_y - 1), fill=TOP)
    draw.rectangle(
        (0, native_height - band_y, native_width - 1, native_height - 1),
        fill=BOTTOM,
    )
    draw.rectangle((0, 0, band_x - 1, native_height - 1), fill=LEFT)
    draw.rectangle(
        (native_width - band_x, 0, native_width - 1, native_height - 1),
        fill=RIGHT,
    )

    crop_vertical = width * native_height > height * native_width
    crop_horizontal = width * native_height < height * native_width
    for position, color in INNER_MARKERS:
        if crop_vertical:
            y = round(native_height * position)
            draw.rectangle((native_width // 2 - 12, y - 12, native_width // 2 + 12, y + 12), fill=color)
        elif crop_horizontal:
            x = round(native_width * position)
            draw.rectangle((x - 12, native_height // 2 - 12, x + 12, native_height // 2 + 12), fill=color)
    draw.rectangle(
        (native_width // 2 - 12, native_height // 2 - 12,
         native_width // 2 + 12, native_height // 2 + 12),
        fill=CENTER,
    )

    output = Image.open(io.BytesIO(resize_to_preset(_png(source), width, height)))
    assert output.format == "PNG"
    assert output.size == (width, height)
    assert output.getpixel((width // 2, height // 2)) == CENTER
    scale = max(width / native_width, height / native_height)
    scaled_width = round(native_width * scale)
    scaled_height = round(native_height * scale)
    offset_x = (scaled_width - width) // 2
    offset_y = (scaled_height - height) // 2
    vertical_edge_lost = offset_y >= band_y * scale
    horizontal_edge_lost = offset_x >= band_x * scale
    assert output.getpixel((width // 2, 0)) == pytest.approx(
        BACKGROUND if vertical_edge_lost else TOP, abs=3
    )
    assert output.getpixel((width // 2, height - 1)) == pytest.approx(
        BACKGROUND if vertical_edge_lost else BOTTOM, abs=3
    )
    assert output.getpixel((0, height // 2)) == pytest.approx(
        BACKGROUND if horizontal_edge_lost else LEFT, abs=3
    )
    assert output.getpixel((width - 1, height // 2)) == pytest.approx(
        BACKGROUND if horizontal_edge_lost else RIGHT, abs=3
    )
    for position, color in INNER_MARKERS:
        if crop_vertical:
            y = round(round(native_height * position) * scale) - offset_y
            if 12 < y < height - 12:
                assert output.getpixel((width // 2, y)) == color
        elif crop_horizontal:
            x = round(round(native_width * position) * scale) - offset_x
            if 12 < x < width - 12:
                assert output.getpixel((x, height // 2)) == color

    if crop_vertical:
        removed = 100 * (1 - native_width * height / (native_height * width))
    elif crop_horizontal:
        removed = 100 * (1 - native_height * width / (native_width * height))
    else:
        removed = 0.0
    assert removed == pytest.approx(EXPECTED_REMOVED_PERCENT[preset_id], abs=0.01)


@pytest.mark.parametrize("preset_id", PLATFORM_PRESETS)
@pytest.mark.parametrize("placement", ["corner", "prominent", "watermark", "auto"])
def test_logo_overlay_stays_inside_each_final_canvas_and_keeps_proportions(
    preset_id, placement
):
    width, height, _label = PLATFORM_PRESETS[preset_id]
    base = Image.new("RGB", (width, height), BACKGROUND)
    logo = Image.new("RGBA", (300, 100), (0, 255, 0, 255))

    output = Image.open(io.BytesIO(apply_logo(_png(base), _png(logo), placement)))
    assert output.format == "PNG"
    assert output.size == (width, height)
    bounds = ImageChops.difference(output.convert("RGB"), base).getbbox()
    assert bounds is not None
    left, top, right, bottom = bounds
    assert 0 <= left < right <= width
    assert 0 <= top < bottom <= height
    assert width - right == WATERMARK_MARGIN_PX
    assert (top if placement in ("prominent", "auto") else height - bottom) == WATERMARK_MARGIN_PX
    assert (right - left) / (bottom - top) == pytest.approx(3, abs=0.04)

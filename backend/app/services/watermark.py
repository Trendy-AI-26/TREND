import io

from PIL import Image

WATERMARK_SCALE = 0.15
WATERMARK_OPACITY = 0.70
WATERMARK_MARGIN_PX = 20
CORNER_SCALE = 0.18
PROMINENT_SCALE = 0.34
FULL_OPACITY = 1.0


def _placement_settings(placement: str) -> tuple[float, float, str]:
    if placement == "prominent":
        return PROMINENT_SCALE, FULL_OPACITY, "top_right"
    if placement == "watermark":
        return WATERMARK_SCALE, WATERMARK_OPACITY, "bottom_right"
    if placement == "auto":
        return CORNER_SCALE, FULL_OPACITY, "top_right"
    # "corner" is the standard exact-logo placement.
    return CORNER_SCALE, FULL_OPACITY, "bottom_right"


def apply_logo(
    image_bytes: bytes,
    logo_bytes: bytes,
    placement: str,
) -> bytes:
    """Overlay the exact uploaded logo without changing its proportions."""
    if placement == "none":
        return image_bytes

    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    scale_limit, opacity, anchor = _placement_settings(placement)

    max_logo_w = max(1, round(base.width * scale_limit))
    max_logo_h = max(1, base.height - (2 * WATERMARK_MARGIN_PX))
    scale = min(max_logo_w / logo.width, max_logo_h / logo.height)
    target_logo_w = max(1, round(logo.width * scale))
    target_logo_h = max(1, round(logo.height * scale))
    logo = logo.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)

    if opacity < FULL_OPACITY:
        r, g, b, a = logo.split()
        a = a.point(lambda px: int(px * opacity))
        logo = Image.merge("RGBA", (r, g, b, a))

    if anchor == "top_right":
        x = base.width - target_logo_w - WATERMARK_MARGIN_PX
        y = WATERMARK_MARGIN_PX
    else:
        x = base.width - target_logo_w - WATERMARK_MARGIN_PX
        y = base.height - target_logo_h - WATERMARK_MARGIN_PX

    base.alpha_composite(logo, dest=(x, y))

    out = io.BytesIO()
    base.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def apply_watermark(image_bytes: bytes, logo_bytes: bytes) -> bytes:
    """Backward-compatible wrapper for the legacy watermark path."""
    return apply_logo(image_bytes, logo_bytes, "watermark")

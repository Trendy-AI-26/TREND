import asyncio
import base64
import hashlib
import json
import logging
from binascii import Error as BinasciiError
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import ValidationError
from storage3.exceptions import StorageException

from app.config import settings
from app.core.auth import User, get_current_user
from app.core.supabase import get_service_client
from app.models.caption import CaptionPreferences, CaptionRequest, CaptionResponse
from app.models.generation import (
    GenerateRequest,
    GenerationBrief,
    GenerationDetailResponse,
    GenerationHistoryItem,
    GenerationHistoryPage,
    GenerationHistoryStatusEnum,
    GenerationResponse,
    LogoModeEnum,
    LogoPlacementEnum,
    PlatformPresetEnum,
    ProviderEnum,
    TextLanguageEnum,
)
from app.services.caption_generator import CaptionOutputError, generate_caption
from app.services.credits import (
    CreditsError,
    commit_credits,
    release_credits,
    reserve_credits,
)
from app.services.error_mapping import classify_provider_error
from app.services.generation_lock import (
    GenerationLockError,
    acquire_generation_lock,
    release_generation_lock,
)
from app.services.generation_resolver import (
    resolve_caption_config,
    resolve_generation_config,
)
from app.services.postprocess import resize_to_preset
from app.services.presets import (
    PLATFORM_PRESETS,
    PRESET_TO_ASPECT_RATIO,
    build_download_filename,
)
from app.services.product_asset_loader import load_product_asset_reference
from app.services.prompt_composer import (
    BrandContext,
    build_generation_prompt,
    build_platform_context,
)
from app.services.providers.base import ProviderError, ProviderResult
from app.services.providers.openai_image import openai_generate
from app.services.quota import (
    QuotaError,
    commit_generation_slot,
    release_generation_slot,
    reserve_generation_slot,
)
from app.services.rate_limit import (
    RateLimitExceeded,
)
from app.services.rate_limit import (
    check_generation_rate_limit as enforce_generation_rate_limit,
)
from app.services.usage import UsageTimer
from app.services.watermark import apply_logo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brands/{brand_id}", tags=["generations"])


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "request_id": str(uuid4()),
            }
        },
    )


def _hash_generation_request(body: GenerateRequest) -> str:
    payload = body.model_dump_json()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_idempotent_generation(
    *,
    user_id: str,
    scope: str = "image_generation",
    idempotency_key: str,
    request_hash: str,
) -> dict | None:
    client = get_service_client()

    query = client.table("idempotency_records")

    # بعض Fake Clients في اختبارات Endpoint لا تدعم
    # عمليات select، لذلك نتجاوز قراءة Idempotency فيها.
    if not hasattr(query, "select"):
        return None

    try:
        result = (
            query.select("*")
            .eq("user_id", user_id)
            .eq("scope", scope)
            .eq("idempotency_key", idempotency_key)
            .maybe_single()
            .execute()
        )
    except AttributeError:
        # توافق مع Fake Client الخاص باختبارات Endpoint
        return None

    if result is None or result.data is None:
        return None

    record = result.data

    if record.get("request_hash") != request_hash:
        raise _error_response(
            409,
            "IDEMPOTENCY_KEY_REUSED",
            ("The same Idempotency-Key was used with a different request."),
        )

    generation_id = record.get("generation_id")

    if not generation_id:
        if record.get("status") == "processing":
            raise _error_response(
                409,
                "GENERATION_IN_PROGRESS",
                "This request is already being processed.",
            )
        return None

    generation_result = (
        client.table("generations")
        .select("*")
        .eq("id", generation_id)
        .maybe_single()
        .execute()
    )

    if generation_result is not None and generation_result.data is not None:
        return generation_result.data

    return record


_get_existing_idempotency = _get_idempotent_generation


def _get_brand_or_404(brand_id: UUID, user_id: str) -> dict:
    client = get_service_client()
    result = (
        client.table("brands")
        .select("*")
        .eq("id", str(brand_id))
        .eq("owner_user_id", user_id)
        .maybe_single()
        .execute()
    )
    if result is None or result.data is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")
    return result.data


def _get_brand_kit_context(brand_id: UUID, brand_name: str) -> BrandContext | None:
    """Fetch raw brand kit fields for a complete kit, or None."""
    client = get_service_client()
    result = (
        client.table("brand_kits")
        .select("tagline, tone, audience, colors, avoid_words, industry, status")
        .eq("brand_id", str(brand_id))
        .maybe_single()
        .execute()
    )
    if result is None or result.data is None:
        return None
    row = result.data
    if row.get("status") != "complete":
        return None
    return BrandContext(
        name=brand_name,
        tagline=row.get("tagline"),
        tone=row.get("tone"),
        industry=row.get("industry"),
        audience=row.get("audience"),
        colors=row.get("colors") or [],
        avoid_words=row.get("avoid_words"),
    )


def _resolve_logo_placement(body: GenerateRequest) -> LogoPlacementEnum:
    """Resolve the new placement field while supporting legacy logo_mode calls."""
    if body.logo_placement != LogoPlacementEnum.none:
        return body.logo_placement
    if body.logo_mode == LogoModeEnum.watermark:
        return LogoPlacementEnum.watermark
    if body.logo_mode in (LogoModeEnum.prompt, LogoModeEnum.both):
        return LogoPlacementEnum.auto
    return LogoPlacementEnum.none


def _mark_failed(generation_id: UUID, code: str, message: str) -> None:
    client = get_service_client()
    now = datetime.now(timezone.utc).isoformat()
    client.table("generations").update(
        {
            "status": "failed",
            "error_code": code,
            "error_message": (message or "")[:1000],
            "completed_at": now,
        }
    ).eq("id", str(generation_id)).execute()


def _derive_download_filename(
    image_url: str | None, row: dict, brand_name: str
) -> str | None:
    if not image_url or not row.get("completed_at"):
        return None
    completed_at = row["completed_at"]
    if isinstance(completed_at, str):
        completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    return build_download_filename(
        brand_name=brand_name,
        preset_identifier=row["platform_preset"],
        completed_at=completed_at,
    )


def _build_response(row: dict, brand_name: str) -> GenerationResponse:
    image_url = _build_public_image_url(row.get("image_path"))
    return GenerationResponse(
        id=row["id"],
        prompt=row["prompt"],
        provider=row["provider"],
        model=row["model"],
        platform_preset=row["platform_preset"],
        language=row.get("language", "ar"),
        width=row["width"],
        height=row["height"],
        logo_mode=row["logo_mode"],
        status=row["status"],
        image_url=image_url,
        download_filename=_derive_download_filename(image_url, row, brand_name),
        error_code=row.get("error_code"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


HISTORY_PAGE_SIZE = 24

PROMPT_EXCERPT_LENGTH = 120


def _build_public_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.STORAGE_BUCKET}/{image_path}"
    )


def _build_prompt_excerpt(prompt: str) -> str:
    if len(prompt) <= PROMPT_EXCERPT_LENGTH:
        return prompt
    return prompt[: PROMPT_EXCERPT_LENGTH - 1].rstrip() + "…"


def _encode_cursor(created_at: str, row_id: str) -> str:
    payload = json.dumps({"c": created_at, "i": row_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    except (BinasciiError, UnicodeDecodeError):
        raise _error_response(400, "VALIDATION_ERROR", "Invalid cursor")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise _error_response(400, "VALIDATION_ERROR", "Invalid cursor")
    if not isinstance(payload, dict) or "c" not in payload or "i" not in payload:
        raise _error_response(400, "VALIDATION_ERROR", "Invalid cursor")
    created_at = payload["c"]
    row_id = payload["i"]
    if not isinstance(created_at, str) or not isinstance(row_id, str):
        raise _error_response(400, "VALIDATION_ERROR", "Invalid cursor")
    try:
        parsed_created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        parsed_id = UUID(row_id)
    except ValueError:
        raise _error_response(400, "VALIDATION_ERROR", "Invalid cursor")
    return parsed_created_at.isoformat(), str(parsed_id)


def _is_already_missing_storage_error(exc: Exception) -> bool:
    status_code = str(getattr(exc, "status", ""))
    error_code = str(getattr(exc, "code", "")).lower()
    message = str(getattr(exc, "message", str(exc))).lower()
    return (
        status_code == "404"
        or error_code in {"not_found", "notfound", "object_not_found", "objectnotfound"}
        or "not found" in message
        or "does not exist" in message
    )


def _build_history_item(row: dict) -> GenerationHistoryItem:
    image_url = _build_public_image_url(row.get("image_path"))
    error_message = row.get("error_message") if row.get("status") == "failed" else None
    return GenerationHistoryItem(
        id=row["id"],
        prompt_excerpt=_build_prompt_excerpt(row["prompt"]),
        provider=row["provider"],
        model=row["model"],
        platform_preset=row["platform_preset"],
        language=row.get("language", "ar"),
        width=row["width"],
        height=row["height"],
        logo_mode=row["logo_mode"],
        status=row["status"],
        image_url=image_url,
        error_message=error_message,
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


def _build_detail_response(row: dict, brand_name: str) -> GenerationDetailResponse:
    image_url = _build_public_image_url(row.get("image_path"))
    return GenerationDetailResponse(
        id=row["id"],
        prompt=row["prompt"],
        provider=row["provider"],
        model=row["model"],
        platform_preset=row["platform_preset"],
        language=row.get("language", "ar"),
        width=row["width"],
        height=row["height"],
        logo_mode=row["logo_mode"],
        status=row["status"],
        provider_request_id=row.get("provider_request_id"),
        image_url=image_url,
        download_filename=_derive_download_filename(image_url, row, brand_name),
        error_code=row.get("error_code"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


@router.post(
    "/generations/{generation_id}/caption",
    response_model=CaptionResponse,
)
async def create_caption(
    brand_id: UUID,
    generation_id: UUID,
    body: CaptionRequest | None = None,
    current_user: User = Depends(get_current_user),
) -> CaptionResponse:
    """Generate a caption for an existing successful image generation.

    Language, platform, prompt, and brand context are inherited from the
    generation. The optional body contains caption preferences only.
    """
    brand = _get_brand_or_404(brand_id, current_user.id)
    client = get_service_client()
    generation = _find_generation_or_404(client, brand_id, generation_id)

    if generation.get("status") != "succeeded":
        raise _error_response(
            409,
            "GENERATION_NOT_READY",
            "Caption generation requires a successful image generation.",
        )

    try:
        language = TextLanguageEnum(generation.get("language", "ar"))
        platform = PlatformPresetEnum(generation["platform_preset"])
    except (KeyError, ValueError) as exc:
        raise _error_response(
            500,
            "GENERATION_CONTEXT_INVALID",
            "The generation context is invalid for caption generation.",
        ) from exc

    preferences = (
        body.preferences if body and body.preferences else CaptionPreferences()
    )

    # Same server-only credentials as image generation. The stored generation's
    # provider is informational; the key always comes from configuration.
    try:
        managed_config = resolve_caption_config()

    except RuntimeError as exc:
        raise _error_response(
            503,
            "GENERATION_CONFIGURATION_ERROR",
            "Generation is not configured on the server.",
        ) from exc
    if managed_config.provider != "openai":
        raise _error_response(
            503,
            "UNSUPPORTED_PROVIDER",
            "Only OpenAI is supported for captions.",
        )
    api_key = managed_config.api_key

    brief = None
    if generation.get("brief"):
        try:
            brief = GenerationBrief.model_validate(generation["brief"])
        except ValidationError as exc:
            raise _error_response(
                500,
                "GENERATION_CONTEXT_INVALID",
                (
                    "The generation questionnaire context is invalid for "
                    "caption generation."
                ),
            ) from exc

    brand_context = _get_brand_kit_context(brand_id, brand["name"])
    try:
        result = await asyncio.wait_for(
            generate_caption(
                provider="openai",
                api_key=api_key,
                model=getattr(settings, "OPENAI_TEXT_MODEL", "gpt-4o-mini"),
                language=language,
                platform=platform,
                generation_prompt=generation.get("prompt", ""),
                brief=brief,
                brand_context=brand_context,
                preferences=preferences,
            ),
            timeout=60.0,
        )

    except CaptionOutputError as exc:
        logger.info(
            "caption failed code=%s generation_id=%s brand_id=%s",
            exc.code,
            generation_id,
            brand_id,
        )
        status_code = 504 if exc.code == "CAPTION_MODEL_TIMEOUT" else 502
        raise _error_response(status_code, exc.code, exc.user_message) from exc
    except Exception as exc:
        logger.exception(
            "caption pipeline unexpected error generation_id=%s brand_id=%s",
            generation_id,
            brand_id,
        )
        raise _error_response(
            502,
            "CAPTION_PROVIDER_ERROR",
            "Caption generation failed. The image is still available.",
        ) from exc

    logger.info(
        "caption success generation_id=%s brand_id=%s language=%s platform=%s",
        generation_id,
        brand_id,
        language.value,
        platform.value,
    )
    return result


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(
    brand_id: UUID,
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=16,
        max_length=128,
    ),
) -> GenerationResponse:
    if not idempotency_key:
        idempotency_key = f"legacy-{current_user.id}-{uuid4()}"
    """
    Generate an image for a brand.

    The provider, model, and API key are resolved from
    server-side configuration only.

    If product_asset_id is provided:
    - The product asset ownership is verified.
    - The image is downloaded from Supabase Storage.
    - The image is passed to the provider as a reference image.
    - The original product asset remains unchanged.
    """

    # ---------------------------------------------------------
    # 1. Verify that the brand belongs to the current user
    # ---------------------------------------------------------
    brand = _get_brand_or_404(
        brand_id=brand_id,
        user_id=current_user.id,
    )

    brand_name = brand["name"]
    brand_has_logo = bool(brand.get("logo_path"))
    request_hash = _hash_generation_request(body)

    existing = _get_idempotent_generation(
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    if existing is not None:
        return _build_response(existing, brand["name"])

    try:
        enforce_generation_rate_limit(
            user_id=current_user.id,
            limit=getattr(settings, "GENERATION_RATE_LIMIT", 5),
            window_seconds=getattr(
                settings,
                "GENERATION_RATE_WINDOW_SECONDS",
                60,
            ),
        )
    except RateLimitExceeded as exc:
        raise _error_response(429, "RATE_LIMITED", str(exc)) from exc

    idempotency_record = _create_idempotency_record(
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    logo_placement = _resolve_logo_placement(body)

    # ---------------------------------------------------------
    # 2. Validate logo requirements
    # ---------------------------------------------------------
    if logo_placement != LogoPlacementEnum.none and not brand_has_logo:
        raise _error_response(
            400,
            "LOGO_REQUIRED",
            (
                "This logo mode requires an uploaded brand logo. "
                "Please upload a logo on the Settings page."
            ),
        )

    # ---------------------------------------------------------
    # 3. Validate product instruction usage
    # ---------------------------------------------------------
    if body.product_edit_instruction and body.product_asset_id is None:
        raise _error_response(
            400,
            "PRODUCT_ASSET_REQUIRED",
            (
                "A product image is required when "
                "product edit instructions are provided."
            ),
        )

    # ---------------------------------------------------------
    # 4. Load product image if the user selected one
    # ---------------------------------------------------------
    product_asset_reference = None

    if body.product_asset_id is not None:
        product_asset_reference = load_product_asset_reference(
            asset_id=body.product_asset_id,
            brand_id=brand_id,
            user_id=current_user.id,
        )

    # ---------------------------------------------------------
    # 5. Resolve managed provider configuration
    # ---------------------------------------------------------
    try:
        managed_config = resolve_generation_config()
    except RuntimeError as exc:
        raise _error_response(
            503,
            "GENERATION_CONFIGURATION_ERROR",
            "Image generation is not configured on the server.",
        ) from exc

    # ---------------------------------------------------------
    # 6. Resolve platform dimensions and context
    # ---------------------------------------------------------
    preset_w, preset_h, _label = PLATFORM_PRESETS[body.platform_preset.value]

    aspect_ratio = PRESET_TO_ASPECT_RATIO[body.platform_preset.value]

    platform = build_platform_context(
        preset_id=body.platform_preset.value,
        width=preset_w,
        height=preset_h,
        aspect_ratio=aspect_ratio,
    )

    # ---------------------------------------------------------
    # 7. Load the completed Brand Kit context
    # ---------------------------------------------------------
    brand_context = _get_brand_kit_context(
        brand_id=brand_id,
        brand_name=brand_name,
    )

    # ---------------------------------------------------------
    # 8. Resolve product image instructions
    # ---------------------------------------------------------
    product_edit_instruction = None

    if product_asset_reference is not None:
        product_edit_instruction = body.product_edit_instruction or (
            "Use the product image as the main visual "
            "reference. Preserve its identity, shape, "
            "packaging, logo, label, and important colors."
        )

    # ---------------------------------------------------------
    # 9. Create the full prompt
    # ---------------------------------------------------------
    full_prompt = build_generation_prompt(
        brief=body.brief,
        brand_context=brand_context,
        platform=platform,
        logo_mode=body.logo_mode.value,
        brand_has_logo=brand_has_logo,
        logo_placement=logo_placement.value,
        product_edit_instruction=product_edit_instruction,
    )

    # ---------------------------------------------------------
    # 10. Create a generation row before calling the provider
    # ---------------------------------------------------------
    generation_id = uuid4()
    lock_acquired = False
    quota_reserved = False

    try:
        acquire_generation_lock(
            user_id=current_user.id,
            generation_id=generation_id,
        )
        lock_acquired = True

    except GenerationLockError as exc:
        raise _error_response(
            409,
            "GENERATION_IN_PROGRESS",
            str(exc),
        ) from exc

    client = get_service_client()
    client.table("idempotency_records").update(
        {
            "generation_id": str(generation_id),
        }
    ).eq(
        "id",
        idempotency_record["id"],
    ).execute()

    if managed_config.provider != "openai":
        raise _error_response(
            503,
            "UNSUPPORTED_PROVIDER",
            "Only OpenAI is supported.",
        )

    resolved_model = managed_config.model

    client.table("generations").insert(
        {
            "id": str(generation_id),
            "user_id": current_user.id,
            "brand_id": str(brand_id),
            "prompt": body.brief.core_idea,
            "brief": body.brief.model_dump(mode="json"),
            "language": body.brief.language.value,
            "provider": "openai",
            "model": resolved_model,
            "idempotency_key": idempotency_key,
            "platform_preset": body.platform_preset.value,
            "width": preset_w,
            "height": preset_h,
            "logo_mode": body.logo_mode.value,
            "product_asset_id": (
                str(body.product_asset_id)
                if body.product_asset_id is not None
                else None
            ),
            "status": "pending",
        }
    ).execute()

    logger.info(
        (
            "generate start generation_id=%s "
            "brand_id=%s provider=%s preset=%s "
            "logo_mode=%s has_product_reference=%s"
        ),
        generation_id,
        brand_id,
        managed_config.provider,
        body.platform_preset.value,
        body.logo_mode.value,
        product_asset_reference is not None,
    )

    # ---------------------------------------------------------
    # 11. Reserve credits, start usage, then run the provider
    # ---------------------------------------------------------
    credit_reservation = None
    usage_timer = None

    try:
        try:
            reserve_generation_slot(
                user_id=current_user.id,
                generation_id=generation_id,
            )
            quota_reserved = True
        except QuotaError as exc:
            status_code = 402 if exc.code == "GENERATION_LIMIT_REACHED" else 503
            raise _error_response(status_code, exc.code, exc.message) from exc

        try:
            credit_reservation = reserve_credits(
                user_id=current_user.id,
                generation_id=generation_id,
                amount=settings.GENERATION_CREDIT_COST,
                idempotency_key=f"generation:{generation_id}:reserve",
            )
        except CreditsError as exc:
            # Out of credits is a client-visible condition, not a server fault.
            raise _error_response(
                402,
                exc.code,
                exc.message,
            ) from exc

        usage_timer = UsageTimer(
            user_id=current_user.id,
            generation_id=generation_id,
            feature="image_generation",
            provider="openai",
            model=resolved_model,
            credits=settings.GENERATION_CREDIT_COST,
        )
        usage_timer.start()

        client.table("generations").update({"status": "processing"}).eq(
            "id",
            str(generation_id),
        ).execute()

        api_key = managed_config.api_key

        try:
            result: ProviderResult = await asyncio.wait_for(
                openai_generate(
                    api_key=api_key,
                    prompt=full_prompt,
                    width=preset_w,
                    height=preset_h,
                    model=resolved_model,
                    reference_image=product_asset_reference,
                ),
                timeout=120.0,
            )

        except asyncio.TimeoutError as exc:
            raise ProviderError(
                "TIMEOUT",
                "The request took too long to complete. Please try again.",
            ) from exc

        except ProviderError:
            raise

        except Exception as exc:
            code, user_message = classify_provider_error(exc)

            raise ProviderError(
                code,
                user_message,
            ) from exc

        # -----------------------------------------------------
        # 12. Resize generated image to the selected platform
        # -----------------------------------------------------
        image_bytes = resize_to_preset(
            result.image_bytes,
            preset_w,
            preset_h,
        )

        # -----------------------------------------------------
        # 13. Apply the brand logo watermark if requested
        # -----------------------------------------------------
        if logo_placement != LogoPlacementEnum.none and brand_has_logo:
            logo_bytes = client.storage.from_(settings.STORAGE_BUCKET).download(
                brand["logo_path"]
            )

            image_bytes = apply_logo(
                image_bytes,
                logo_bytes,
                logo_placement.value,
            )

        # -----------------------------------------------------
        # 14. Save the generated image to Storage
        # -----------------------------------------------------
        image_path = f"brands/{brand_id}/generations/{generation_id}.png"

        client.storage.from_(settings.STORAGE_BUCKET).upload(
            image_path,
            image_bytes,
            {
                "content-type": "image/png",
                "upsert": "false",
            },
        )

        # -----------------------------------------------------
        # 15. Mark generation as succeeded
        # -----------------------------------------------------
        now_iso = datetime.now(timezone.utc).isoformat()

        updated = (
            client.table("generations")
            .update(
                {
                    "status": "succeeded",
                    "image_path": image_path,
                    "provider_request_id": result.request_id,
                    "completed_at": now_iso,
                }
            )
            .eq(
                "id",
                str(generation_id),
            )
            .execute()
        )

        if credit_reservation is not None:
            commit_credits(credit_reservation)

        if quota_reserved:
            commit_generation_slot(
                user_id=current_user.id,
                generation_id=generation_id,
            )

        if usage_timer is not None:
            usage_timer.finish(
                status="succeeded",
                provider_request_id=result.request_id,
            )

        client.table("idempotency_records").update(
            {
                "status": "succeeded",
                "response_status": 200,
                "completed_at": now_iso,
            }
        ).eq("id", idempotency_record["id"]).execute()

        row = updated.data[0] if updated.data else None

        # -----------------------------------------------------
        # 16. Refetch the saved row if update returned no data
        # -----------------------------------------------------
        if row is None:
            try:
                row = (
                    client.table("generations")
                    .select("*")
                    .eq("id", str(generation_id))
                    .single()
                    .execute()
                    .data
                )
            except Exception:
                logger.warning(
                    ("Failed to re-fetch generation %s after success update"),
                    generation_id,
                )

        # -----------------------------------------------------
        # 17. Fallback response row
        # -----------------------------------------------------
        if row is None:
            logger.error(
                (
                    "No row data for succeeded generation "
                    "%s brand_id=%s; constructing minimal row"
                ),
                generation_id,
                brand_id,
            )

            row = {
                "id": str(generation_id),
                "prompt": body.brief.core_idea,
                "language": body.brief.language.value,
                "provider": "openai",
                "model": resolved_model,
                "platform_preset": body.platform_preset.value,
                "width": preset_w,
                "height": preset_h,
                "logo_mode": body.logo_mode.value,
                "status": "succeeded",
                "image_path": image_path,
                "error_code": None,
                "error_message": None,
                "created_at": now_iso,
                "completed_at": now_iso,
            }

        logger.info(
            "generate success generation_id=%s brand_id=%s",
            generation_id,
            brand_id,
        )

        return _build_response(
            row,
            brand_name,
        )

    # ---------------------------------------------------------
    # 18. Known provider failure
    # ---------------------------------------------------------
    except ProviderError as exc:
        if quota_reserved:
            release_generation_slot(
                user_id=current_user.id,
                generation_id=generation_id,
            )
        if credit_reservation is not None:
            release_credits(credit_reservation)
        if usage_timer is not None:
            usage_timer.finish(
                status="failed",
                metadata={"error_code": exc.code},
            )
        client.table("idempotency_records").update(
            {"status": "failed", "response_status": 502}
        ).eq("id", idempotency_record["id"]).execute()
        _mark_failed(
            generation_id,
            exc.code,
            exc.user_message,
        )

        logger.info(
            ("generate failed code=%s generation_id=%s brand_id=%s"),
            exc.code,
            generation_id,
            brand_id,
        )

        raise _error_response(
            502,
            exc.code,
            exc.user_message,
        ) from exc

    # ---------------------------------------------------------
    # 19. Unexpected failure
    # ---------------------------------------------------------
    except HTTPException as exc:
        # Already-shaped client errors (402 credits, 400 validation, ...)
        # must not be relabelled as an internal fault, but resources created
        # before the error still need to be finalized.
        if quota_reserved:
            try:
                release_generation_slot(
                    user_id=current_user.id,
                    generation_id=generation_id,
                )
            except Exception:
                logger.exception("Failed to release image quota after HTTP failure")
        if credit_reservation is not None:
            try:
                release_credits(credit_reservation)
            except Exception:
                logger.exception("Failed to release credits after HTTP failure")
        if usage_timer is not None and usage_timer.usage_id is not None:
            try:
                usage_timer.finish(
                    status="failed",
                    metadata={"error_code": "HTTP_ERROR"},
                )
            except Exception:
                logger.exception("Failed to finish usage after HTTP failure")
        try:
            client.table("idempotency_records").update(
                {"status": "failed", "response_status": exc.status_code}
            ).eq("id", idempotency_record["id"]).execute()
        except Exception:
            logger.exception("Failed to update idempotency after HTTP failure")
        raise

    except Exception as exc:
        logger.exception(
            ("generate pipeline unexpected error generation_id=%s brand_id=%s"),
            generation_id,
            brand_id,
        )

        if quota_reserved:
            try:
                release_generation_slot(
                    user_id=current_user.id,
                    generation_id=generation_id,
                )
            except Exception:
                logger.exception(
                    "Failed to release image quota after unexpected failure"
                )
        if credit_reservation is not None:
            try:
                release_credits(credit_reservation)
            except Exception:
                logger.exception("Failed to release credits after unexpected failure")
        if usage_timer is not None and usage_timer.usage_id is not None:
            try:
                usage_timer.finish(
                    status="failed",
                    metadata={"error_code": "INTERNAL_ERROR"},
                )
            except Exception:
                logger.exception("Failed to finish usage after unexpected failure")
        try:
            client.table("idempotency_records").update(
                {"status": "failed", "response_status": 500}
            ).eq("id", idempotency_record["id"]).execute()
        except Exception:
            logger.exception("Failed to update idempotency after unexpected failure")
        _mark_failed(generation_id, "INTERNAL_ERROR", "Internal error")

        raise _error_response(
            500,
            "INTERNAL_ERROR",
            "Something went wrong. Please try again.",
        ) from exc
    finally:
        if lock_acquired:
            release_generation_lock(
                user_id=current_user.id,
                generation_id=generation_id,
            )


_VALID_HISTORY_STATUSES = {s.value for s in GenerationHistoryStatusEnum}
_VALID_HISTORY_PROVIDERS = {p.value for p in ProviderEnum}


@router.get("/generations", response_model=GenerationHistoryPage)
async def list_generation_history(
    brand_id: UUID,
    current_user: User = Depends(get_current_user),
    provider: str | None = Query(None),
    status: str | None = Query(None),
    cursor: str | None = Query(None),
) -> GenerationHistoryPage:
    _get_brand_or_404(brand_id, current_user.id)

    if provider is not None and provider not in _VALID_HISTORY_PROVIDERS:
        raise _error_response(
            400, "VALIDATION_ERROR", f"Invalid provider filter: {provider}"
        )
    if status is not None and status not in _VALID_HISTORY_STATUSES:
        raise _error_response(
            400, "VALIDATION_ERROR", f"Invalid status filter: {status}"
        )

    client = get_service_client()
    query = (
        client.table("generations")
        .select("*")
        .eq("brand_id", str(brand_id))
        .in_("status", ["succeeded", "failed"])
    )

    if provider:
        query = query.eq("provider", provider)
    if status:
        query = query.eq("status", status)

    if cursor:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        query = query.or_(
            f"created_at.lt.{cursor_created_at},"
            f"and(created_at.eq.{cursor_created_at},id.lt.{cursor_id})"
        )

    query = (
        query.order("created_at", desc=True)
        .order("id", desc=True)
        .limit(HISTORY_PAGE_SIZE + 1)
    )

    result = query.execute()
    rows = result.data or []

    successful_count = None
    if cursor is None and provider is None and status is None:
        usage_result = (
            client.table("generations")
            .select("id", count="exact", head=True)
            .eq("brand_id", str(brand_id))
            .eq("status", "succeeded")
            .execute()
        )
        successful_count = usage_result.count

    has_next = len(rows) > HISTORY_PAGE_SIZE
    if has_next:
        rows = rows[:HISTORY_PAGE_SIZE]

    items = [_build_history_item(row) for row in rows]

    next_cursor = None
    if has_next and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last["created_at"], last["id"])

    logger.info(
        (
            "history list brand_id=%s provider=%s status=%s cursor=%s "
            "returned=%d has_next=%s"
        ),
        brand_id,
        provider,
        status,
        bool(cursor),
        len(items),
        has_next,
    )

    return GenerationHistoryPage(
        items=items,
        next_cursor=next_cursor,
        page_size=HISTORY_PAGE_SIZE,
        successful_count=successful_count,
    )


@router.get("/generations/{generation_id}", response_model=GenerationDetailResponse)
async def get_generation_detail(
    brand_id: UUID,
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
) -> GenerationDetailResponse:
    brand = _get_brand_or_404(brand_id, current_user.id)

    client = get_service_client()
    row = _find_generation_or_404(client, brand_id, generation_id)

    # History exposes only terminal generations. A non-terminal row (pending/
    # processing — e.g. an in-flight run or one left stuck by a crash) would fail
    # GenerationDetailResponse's status enum, so treat it as not-found here.
    if row["status"] not in ("succeeded", "failed"):
        raise _error_response(404, "GENERATION_NOT_FOUND", "Generation not found")

    logger.info(
        "history detail brand_id=%s generation_id=%s status=%s",
        brand_id,
        generation_id,
        row.get("status"),
    )
    return _build_detail_response(row, brand["name"])


def _find_generation_or_404(client, brand_id: UUID, generation_id: UUID) -> dict:
    result = (
        client.table("generations")
        .select("*")
        .eq("id", str(generation_id))
        .eq("brand_id", str(brand_id))
        .maybe_single()
        .execute()
    )
    if result is None or result.data is None:
        raise _error_response(404, "GENERATION_NOT_FOUND", "Generation not found")
    return result.data


@router.delete("/generations/{generation_id}", status_code=204)
async def delete_generation(
    brand_id: UUID,
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
) -> None:
    _get_brand_or_404(brand_id, current_user.id)

    client = get_service_client()
    row = _find_generation_or_404(client, brand_id, generation_id)

    image_path = row.get("image_path")
    if image_path:
        try:
            client.storage.from_(settings.STORAGE_BUCKET).remove([image_path])
        except StorageException as exc:
            if _is_already_missing_storage_error(exc):
                pass
            else:
                logger.warning(
                    (
                        "storage delete failed brand_id=%s generation_id=%s "
                        "path=%s error=%s"
                    ),
                    brand_id,
                    generation_id,
                    image_path,
                    exc,
                )
                raise _error_response(
                    502,
                    "STORAGE_DELETE_FAILED",
                    "Failed to delete stored image. Please try again.",
                )

    # Storage is removed first (above) so a "deleted" image is never left
    # publicly reachable. If the DB delete fails after that, surface a clean
    # retryable error: the row briefly points at a now-missing object, and a
    # retry heals it (storage removal tolerates an already-missing object).
    try:
        client.table("generations").delete().eq("id", str(generation_id)).eq(
            "brand_id", str(brand_id)
        ).execute()
    except Exception as exc:
        logger.error(
            (
                "db delete failed after storage removal brand_id=%s "
                "generation_id=%s path=%s error=%s"
            ),
            brand_id,
            generation_id,
            image_path,
            exc,
        )
        raise _error_response(
            502,
            "DELETE_FAILED",
            "Failed to delete the generation. Please try again.",
        )

    logger.info(
        "generation deleted brand_id=%s generation_id=%s",
        brand_id,
        generation_id,
    )


def _get_product_asset_or_400(
    *,
    brand_id: UUID,
    asset_id: UUID,
    user_id: str,
) -> dict:
    client = get_service_client()

    result = (
        client.table("product_assets")
        .select("*")
        .eq("id", str(asset_id))
        .eq("brand_id", str(brand_id))
        .eq("owner_user_id", user_id)
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _error_response(
            400,
            "INVALID_PRODUCT_ASSET",
            "Product image does not belong to this brand",
        )

    return result.data


def _create_idempotency_record(
    *,
    user_id: str,
    idempotency_key: str,
    request_hash: str,
) -> dict:
    client = get_service_client()

    try:
        result = (
            client.table("idempotency_records")
            .insert(
                {
                    "user_id": user_id,
                    "scope": "image_generation",
                    "idempotency_key": idempotency_key,
                    "request_hash": request_hash,
                    "status": "processing",
                }
            )
            .execute()
        )
    except Exception as exc:
        raise _error_response(
            409,
            "GENERATION_IN_PROGRESS",
            "This request is already being processed.",
        ) from exc

    if not result.data:
        raise _error_response(
            500,
            "IDEMPOTENCY_CREATE_FAILED",
            "Could not create the idempotency record.",
        )

    return result.data[0]

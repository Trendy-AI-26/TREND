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

from app import db
from app.config import settings
from app.core import storage
from app.core.auth import User, get_current_user
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
from app.repositories import brands as brand_repo
from app.repositories import generations as gen_repo
from app.repositories import product_assets as product_asset_repo
from app.services.caption_generator import CaptionOutputError, generate_caption
from app.services.credits import (
    CreditReservation,
    CreditsError,
    commit_credits,
    release_credits,
    reserve_credits,
)
from app.services.trend_service import (
    get_active_trend_or_404,
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


def _hash_generation_request(body: GenerateRequest, *, user_id: str, brand_id: UUID) -> str:
    """Bind an idempotency key to the user, brand and validated payload.

    The body is the validated model (defaults included), so equivalent payloads
    hash identically regardless of key order. Reusing a key for another user,
    brand or payload produces a different hash and is rejected.
    """
    payload = json.dumps(
        {
            "version": 1,
            "user_id": str(user_id),
            "brand_id": str(brand_id),
            "body": body.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _save_checkpoint(record_id: str, checkpoint: dict) -> None:
    if not gen_repo.save_checkpoint(record_id, checkpoint):
        raise RuntimeError("Settlement checkpoint was not saved")


def _resume_settlement(record: dict, checkpoint: dict) -> dict:
    """One bounded settlement attempt; replays reuse the same idempotent receipts.

    Never compensate a commit failure: its transaction may already have
    committed. The checkpoint is immutable once published, including during
    concurrent replays. Success is published (generation + idempotency record)
    only after the credit and quota commits have returned.
    """
    user_id, generation_id = str(record["user_id"]), str(record["generation_id"])
    reservation = (
        CreditReservation(
            user_id=user_id,
            generation_id=generation_id,
            reservation_id=checkpoint["credit_id"],
            amount=checkpoint["credit_amount"],
        )
        if checkpoint.get("credit_id")
        else None
    )
    try:
        if checkpoint["phase"] == "output_ready":
            if reservation:
                commit_credits(reservation)
            if checkpoint["quota_reserved"]:
                commit_generation_slot(user_id=user_id, generation_id=UUID(generation_id))
            row = gen_repo.mark_succeeded(
                generation_id,
                checkpoint["image_path"],
                checkpoint.get("provider_request_id"),
                checkpoint["completed_at"],
            )
            status, response_status = "succeeded", 200
        else:
            failures = []
            # Neither cleanup attempt may prevent the other from running.
            if checkpoint["quota_reserved"]:
                try:
                    release_generation_slot(
                        user_id=user_id, generation_id=UUID(generation_id)
                    )
                except Exception:
                    failures.append("quota")
                    logger.exception("Quota cleanup pending for %s", generation_id)
            if reservation:
                try:
                    release_credits(reservation)
                except Exception:
                    failures.append("credits")
                    logger.exception("Credit cleanup pending for %s", generation_id)
            if failures:
                raise RuntimeError("Cleanup pending: " + ", ".join(failures))
            _mark_failed(
                UUID(generation_id), checkpoint["error_code"], checkpoint["error_message"]
            )
            row = gen_repo.get_generation(generation_id)
            status, response_status = "failed", checkpoint["response_status"]
        if not row:
            raise RuntimeError("Generation finalization returned no row")
        if not gen_repo.finish_idempotency(
            record["id"], status, response_status, checkpoint["completed_at"]
        ):
            raise RuntimeError("Request finalization returned no row")
        try:
            release_generation_lock(user_id=user_id, generation_id=UUID(generation_id))
        except Exception:
            # The generation is already terminal; an expired lock is harmless.
            logger.exception("Could not release owned terminal lock %s", generation_id)
        return row
    except Exception as exc:
        logger.exception("Generation recovery pending for %s", generation_id)
        raise _error_response(
            503,
            "GENERATION_SETTLEMENT_PENDING",
            "Finalization is pending. Retry this request with the same key.",
        ) from exc


def _finish_usage(timer, **kwargs) -> None:
    """Usage logging is best effort and never changes the generation outcome."""
    if timer is not None and getattr(timer, "usage_id", "set") is not None:
        try:
            timer.finish(**kwargs)
        except Exception:
            logger.exception("Usage logging failed; generation outcome is unchanged")


def _get_idempotent_generation(
    *,
    user_id: str,
    scope: str = "image_generation",
    idempotency_key: str,
    request_hash: str,
) -> dict | None:
    """Return the saved successful generation for a replayed key, else None.

    Saved failures and unfinished requests raise the stored/appropriate error;
    the provider is never called again for a key that has an admitted record.
    """
    record = gen_repo.get_idempotency(user_id, scope, idempotency_key)

    if record is None:
        return None

    if record.get("request_hash") != request_hash:
        raise _error_response(
            409,
            "IDEMPOTENCY_KEY_REUSED",
            ("The same Idempotency-Key was used with a different request."),
        )

    generation_id = record.get("generation_id")

    if not generation_id:
        raise _error_response(
            409,
            "GENERATION_OUTCOME_UNKNOWN",
            "This request cannot be safely restarted.",
        )

    row = gen_repo.get_generation(generation_id)
    if row is None:
        raise _error_response(
            409,
            "GENERATION_OUTCOME_UNKNOWN",
            "This request cannot be safely restarted.",
        )

    checkpoint = record.get("response_body") or {}
    if record.get("status") == "processing" and checkpoint.get("phase") in (
        "output_ready",
        "cleanup_pending",
    ):
        row = _resume_settlement(record, checkpoint)
        if row["status"] == "succeeded":
            return row
        raise _error_response(
            checkpoint["response_status"],
            checkpoint["error_code"],
            checkpoint["error_message"],
        )
    if record.get("status") == "processing" and checkpoint.get("phase") == "outcome_unknown":
        raise _error_response(
            503,
            "GENERATION_OUTCOME_UNKNOWN",
            "The provider outcome needs review. This request will not be restarted.",
        )
    if record.get("status") == "processing" or row["status"] in ("pending", "processing"):
        raise _error_response(
            409,
            "GENERATION_IN_PROGRESS",
            "This request is still processing. Retry with the same key.",
        )
    if record.get("status") == "succeeded" and row["status"] == "succeeded":
        return row
    if record.get("status") == "failed" and row["status"] == "failed":
        status = record.get("response_status") or 500
        raise _error_response(
            status if 400 <= status <= 599 else 500,
            row.get("error_code") or "GENERATION_FAILED",
            row.get("error_message") or "This generation failed.",
        )
    raise _error_response(
        409,
        "GENERATION_OUTCOME_UNKNOWN",
        "This request needs recovery before it can be finalized.",
    )


_get_existing_idempotency = _get_idempotent_generation


def _get_brand_or_404(brand_id: UUID, user_id: str) -> dict:
    brand = brand_repo.get_owned_brand(brand_id, user_id)
    if brand is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")
    return brand


def _get_brand_kit_context(brand_id: UUID, brand_name: str) -> BrandContext | None:
    """Fetch raw brand kit fields for a complete kit, or None."""
    row = brand_repo.get_kit(brand_id)
    if row is None:
        return None
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
    now = datetime.now(timezone.utc).isoformat()
    gen_repo.mark_failed(generation_id, code, (message or "")[:1000], now)


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
    return storage.public_url(settings.STORAGE_BUCKET, image_path)


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
    if isinstance(exc, storage.ObjectNotFoundError):
        return True
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
    generation = _find_generation_or_404(brand_id, generation_id)

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
    """
    Generate an image for a brand.

    An ``Idempotency-Key`` header is required. The key is bound to the user,
    brand and payload: a retry with the same key replays the saved outcome and
    never calls the provider again.

    The provider, model, and API key are resolved from
    server-side configuration only.

    If product_asset_id is provided:
    - The product asset ownership is verified.
    - The image is downloaded from object storage (S3/MinIO).
    - The image is passed to the provider as a reference image.
    - The original product asset remains unchanged.
    """
    if not idempotency_key:
        raise _error_response(
            400, "IDEMPOTENCY_KEY_REQUIRED", "An Idempotency-Key is required."
        )

    # ---------------------------------------------------------
    # 1. Verify that the brand belongs to the current user
    # ---------------------------------------------------------
    brand = _get_brand_or_404(
        brand_id=brand_id,
        user_id=current_user.id,
    )

    brand_name = brand["name"]
    brand_has_logo = bool(brand.get("logo_path"))
    request_hash = _hash_generation_request(
        body, user_id=current_user.id, brand_id=brand_id
    )

    existing = _get_idempotent_generation(
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    if existing is not None:
        return _build_response(existing, brand["name"])

    # Validate the selected trend before creating idempotency or generation
    # records. Invalid or expired selections must be safely retryable.
    selected_trend = None
    if body.trend_id is not None:
        selected_trend = get_active_trend_or_404(body.trend_id)

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
    # 4. Validate product instruction usage
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
    # 5. Load product image if the user selected one
    # ---------------------------------------------------------
    product_asset_reference = None

    if body.product_asset_id is not None:
        product_asset_reference = load_product_asset_reference(
            asset_id=body.product_asset_id,
            brand_id=brand_id,
            user_id=current_user.id,
        )

    # ---------------------------------------------------------
    # 6. Resolve managed provider configuration
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
    # 7. Resolve platform dimensions and context
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
    # 8. Load the completed Brand Kit context
    # ---------------------------------------------------------
    brand_context = _get_brand_kit_context(
        brand_id=brand_id,
        brand_name=brand_name,
    )

    # ---------------------------------------------------------
    # 9. Resolve product image instructions
    # ---------------------------------------------------------
    product_edit_instruction = None

    if product_asset_reference is not None:
        product_edit_instruction = body.product_edit_instruction or (
            "Use the product image as the main visual "
            "reference. Preserve its identity, shape, "
            "packaging, logo, label, and important colors."
        )

    # ---------------------------------------------------------
    # 10. Create the full prompt
    # ---------------------------------------------------------
    full_prompt = build_generation_prompt(
        brief=body.brief,
        brand_context=brand_context,
        platform=platform,
        logo_mode=body.logo_mode.value,
        brand_has_logo=brand_has_logo,
        logo_placement=logo_placement.value,
        product_edit_instruction=product_edit_instruction,
        trend_context=selected_trend,
    )

    # ---------------------------------------------------------
    # 11. Admit the request: generation row first, then lock and
    #     idempotency record (which reference it)
    # ---------------------------------------------------------
    generation_id = uuid4()
    quota_reserved = False

    if managed_config.provider != "openai":
        raise _error_response(
            503,
            "UNSUPPORTED_PROVIDER",
            "Only OpenAI is supported.",
        )

    resolved_model = managed_config.model

    idempotency_record = _admit_generation(
        user_id=current_user.id,
        generation_id=generation_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        generation_row={
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
            "trend_id": (str(body.trend_id) if body.trend_id is not None else None),
            "trend_snapshot": selected_trend,
            "trend_applied": selected_trend is not None,
        },
    )

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
    # 12. Reserve quota and credits, start usage, then run the provider
    # ---------------------------------------------------------
    credit_reservation = None
    usage_timer = None
    provider_started = False
    recovery_checkpoint = None

    try:
        try:
            reserve_generation_slot(
                user_id=current_user.id,
                generation_id=generation_id,
            )
            quota_reserved = True
        except QuotaError as exc:
            if exc.code not in {
                "GENERATION_LIMIT_REACHED",
                "DAILY_GENERATION_LIMIT_REACHED",
                "TRIAL_EXPIRED",
            }:
                # The reserve may have committed: treated as an unknown outcome.
                raise
            status_code = 403 if exc.code == "TRIAL_EXPIRED" else 402
            raise _error_response(status_code, exc.code, exc.message) from exc

        try:
            credit_reservation = reserve_credits(
                user_id=current_user.id,
                generation_id=generation_id,
                amount=settings.GENERATION_CREDIT_COST,
                idempotency_key=f"generation:{generation_id}:reserve",
            )
        except CreditsError as exc:
            if exc.code != "INSUFFICIENT_CREDITS":
                raise
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
        try:
            usage_timer.start()
        except Exception:
            logger.exception("Usage start failed; continuing without usage logging")

        gen_repo.mark_processing(generation_id)

        api_key = managed_config.api_key

        provider_started = True
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
        # 13. Resize generated image to the selected platform
        # -----------------------------------------------------
        image_bytes = resize_to_preset(
            result.image_bytes,
            preset_w,
            preset_h,
        )

        # -----------------------------------------------------
        # 14. Apply the brand logo watermark if requested
        # -----------------------------------------------------
        if logo_placement != LogoPlacementEnum.none and brand_has_logo:
            logo_bytes = storage.download(settings.STORAGE_BUCKET, brand["logo_path"])

            image_bytes = apply_logo(
                image_bytes,
                logo_bytes,
                logo_placement.value,
            )

        # -----------------------------------------------------
        # 15. Save the generated image to Storage
        # -----------------------------------------------------
        image_path = f"brands/{brand_id}/generations/{generation_id}.png"

        storage.upload(
            settings.STORAGE_BUCKET,
            image_path,
            image_bytes,
            "image/png",
            upsert=False,
        )

        # -----------------------------------------------------
        # 16. Persist the output, then settle. Never refund an uncertain
        #     commit: once the checkpoint exists, only a replay may settle.
        # -----------------------------------------------------
        recovery_checkpoint = {
            "phase": "output_ready",
            "image_path": image_path,
            "provider_request_id": result.request_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "credit_id": credit_reservation.reservation_id,
            "credit_amount": credit_reservation.amount,
            "quota_reserved": quota_reserved,
        }
        _save_checkpoint(idempotency_record["id"], recovery_checkpoint)
        row = _resume_settlement(idempotency_record, recovery_checkpoint)
        _finish_usage(
            usage_timer, status="succeeded", provider_request_id=result.request_id
        )

        logger.info(
            "generate success generation_id=%s brand_id=%s",
            generation_id,
            brand_id,
        )

        return _build_response(row, brand_name)

    except (Exception, asyncio.CancelledError) as exc:
        if recovery_checkpoint is not None:
            # Output is saved; settlement resumes from a replay of this key.
            if isinstance(exc, HTTPException):
                raise
            raise _error_response(
                503,
                "GENERATION_SETTLEMENT_PENDING",
                "Finalization needs recovery. Keep the same request key.",
            ) from exc

        definite_rejection = isinstance(exc, ProviderError) and exc.code in {
            "INVALID_KEY",
            "RATE_LIMITED",
            "CONTENT_POLICY",
            "PROVIDER_CLIENT_ERROR",
            "REFERENCE_IMAGE_UNSUPPORTED",
        }
        if (provider_started and not definite_rejection) or isinstance(
            exc, (CreditsError, QuotaError)
        ):
            # The provider (or a reservation) may have acted: keep quota,
            # credits, lock and generation row for review; do not restart.
            try:
                _save_checkpoint(idempotency_record["id"], {"phase": "outcome_unknown"})
            except Exception:
                logger.exception("Failed to record unknown outcome for %s", generation_id)
            _finish_usage(
                usage_timer,
                status="failed",
                metadata={"error_code": "GENERATION_OUTCOME_UNKNOWN"},
            )
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise _error_response(
                503,
                "GENERATION_OUTCOME_UNKNOWN",
                "The outcome needs review. This request will not be restarted.",
            ) from exc

        if isinstance(exc, ProviderError):
            code, message, response_status = exc.code, exc.user_message, 502
        elif isinstance(exc, HTTPException):
            error = exc.detail.get("error", {}) if isinstance(exc.detail, dict) else {}
            code = error.get("code", "HTTP_ERROR")
            message = error.get("message", "Rejected")
            response_status = exc.status_code
        else:
            logger.exception(
                "generate pipeline unexpected error generation_id=%s brand_id=%s",
                generation_id,
                brand_id,
            )
            code, message, response_status = "INTERNAL_ERROR", "Internal error", 500

        checkpoint = {
            "phase": "cleanup_pending",
            "error_code": code,
            "error_message": message,
            "response_status": response_status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "quota_reserved": quota_reserved,
            "credit_id": (
                credit_reservation.reservation_id if credit_reservation else None
            ),
            "credit_amount": credit_reservation.amount if credit_reservation else 0,
        }
        try:
            _save_checkpoint(idempotency_record["id"], checkpoint)
        except Exception as checkpoint_error:
            logger.exception("Could not persist cleanup intent for %s", generation_id)
            raise _error_response(
                503,
                "GENERATION_SETTLEMENT_PENDING",
                "Cleanup needs review. Keep the same request key.",
            ) from checkpoint_error
        _resume_settlement(idempotency_record, checkpoint)
        _finish_usage(usage_timer, status="failed", metadata={"error_code": code})
        if isinstance(exc, asyncio.CancelledError):
            raise
        raise _error_response(response_status, code, message) from exc


_VALID_HISTORY_STATUSES = {s.value for s in GenerationHistoryStatusEnum}
_VALID_HISTORY_PROVIDERS = {p.value for p in ProviderEnum}


@router.get("/generations", response_model=GenerationHistoryPage)
def list_generation_history(
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

    decoded_cursor = _decode_cursor(cursor) if cursor else None

    rows = gen_repo.list_history(
        brand_id,
        provider=provider or None,
        status=status or None,
        cursor=decoded_cursor,
        limit=HISTORY_PAGE_SIZE + 1,
    )

    successful_count = None
    if cursor is None and provider is None and status is None:
        successful_count = gen_repo.count_succeeded(brand_id)

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
def get_generation_detail(
    brand_id: UUID,
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
) -> GenerationDetailResponse:
    brand = _get_brand_or_404(brand_id, current_user.id)

    row = _find_generation_or_404(brand_id, generation_id)

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


def _find_generation_or_404(brand_id: UUID, generation_id: UUID) -> dict:
    row = gen_repo.get_brand_generation(brand_id, generation_id)
    if row is None:
        raise _error_response(404, "GENERATION_NOT_FOUND", "Generation not found")
    return row


@router.delete("/generations/{generation_id}", status_code=204)
async def delete_generation(
    brand_id: UUID,
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
) -> None:
    _get_brand_or_404(brand_id, current_user.id)

    row = _find_generation_or_404(brand_id, generation_id)

    image_path = row.get("image_path")
    if image_path:
        try:
            storage.remove(settings.STORAGE_BUCKET, [image_path])
        except storage.StorageError as exc:
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
        gen_repo.delete_generation(brand_id, generation_id)
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
    asset = product_asset_repo.get_owned_asset(asset_id, brand_id, user_id)

    if asset is None:
        raise _error_response(
            400,
            "INVALID_PRODUCT_ASSET",
            "Product image does not belong to this brand",
        )

    return asset


def _admit_generation(
    *,
    user_id: str,
    generation_id: UUID,
    idempotency_key: str,
    request_hash: str,
    generation_row: dict,
) -> dict:
    """Create the parent row before its dependants; compensate only this attempt.

    The generation row is inserted first, then the per-user lock, then the
    idempotency record that references the generation. Each step is its own
    transaction, and a lost response may still have committed, so a failed
    admission is cleaned up using the preallocated ``generation_id`` (never by
    user or key alone: another request may own those rows). No quota, credit
    or provider work happens before this helper returns.
    """
    try:
        gen_repo.insert_generation(generation_row)
        acquire_generation_lock(user_id=user_id, generation_id=generation_id)
        return _create_idempotency_record(
            user_id=user_id,
            generation_id=generation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except Exception as exc:
        cleanup_errors: list[str] = []
        # Children first (the idempotency record references the generation).
        # A failure of one cleanup step must not prevent the others.
        try:
            gen_repo.delete_idempotency_for_generation(generation_id)
        except Exception:
            cleanup_errors.append("idempotency_records")
            logger.exception(
                "Admission cleanup failed table=idempotency_records generation_id=%s",
                generation_id,
            )
        try:
            release_generation_lock(user_id=user_id, generation_id=generation_id)
        except Exception:
            cleanup_errors.append("generation_locks")
            logger.exception(
                "Admission cleanup failed table=generation_locks generation_id=%s",
                generation_id,
            )
        if "idempotency_records" in cleanup_errors:
            # The child could not be removed (its delete is uncertain), so keep
            # the generation as the parent: mark both terminal for diagnosis and
            # replay rather than letting ON DELETE SET NULL drop the link.
            try:
                _mark_failed(generation_id, "ADMISSION_FAILED", "Admission failed")
                gen_repo.fail_idempotency_for_generation(generation_id, 503)
            except Exception:
                logger.exception(
                    "Admission failure marking failed generation_id=%s", generation_id
                )
        else:
            try:
                gen_repo.delete_owned_generation(user_id, generation_id)
            except Exception:
                cleanup_errors.append("generations")
                logger.exception(
                    "Admission cleanup failed table=generations generation_id=%s",
                    generation_id,
                )
        if cleanup_errors:
            raise _error_response(
                503,
                "GENERATION_ADMISSION_CLEANUP_FAILED",
                "Generation admission could not be finalized.",
            ) from exc
        if isinstance(exc, GenerationLockError) or db.is_unique_violation(exc):
            raise _error_response(
                409,
                "GENERATION_IN_PROGRESS",
                str(exc)
                if isinstance(exc, GenerationLockError)
                else "This request is already being processed.",
            ) from exc
        if isinstance(exc, HTTPException):
            raise
        raise _error_response(
            503,
            "GENERATION_ADMISSION_FAILED",
            "Generation admission is temporarily unavailable.",
        ) from exc


def _create_idempotency_record(
    *,
    user_id: str,
    idempotency_key: str,
    request_hash: str,
    generation_id: UUID,
) -> dict:
    try:
        record = gen_repo.create_idempotency(
            user_id,
            "image_generation",
            idempotency_key,
            request_hash,
            generation_id=generation_id,
        )
    except Exception as exc:
        # Only a duplicate key means "already being processed"; any other
        # failure is a real fault and must not be disguised as a duplicate.
        if not db.is_unique_violation(exc):
            raise
        raise _error_response(
            409,
            "GENERATION_IN_PROGRESS",
            "This request is already being processed.",
        ) from exc

    if not record:
        raise _error_response(
            500,
            "IDEMPOTENCY_CREATE_FAILED",
            "Could not create the idempotency record.",
        )

    return record

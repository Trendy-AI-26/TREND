from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class ManagedGenerationConfig:
    provider: str
    api_key: str
    model: str


# توافق مع أي كود قديم يستخدم هذا الاسم
GenerationConfig = ManagedGenerationConfig


def _get_server_value(
    *,
    generation_name: str | None = None,
    managed_name: str,
    default_name: str,
    default: str = "",
) -> str:
    """Read a server-only value.

    Render's GENERATION_* values take precedence. MANAGED_* and the
    IMAGE_/OPENAI_* values remain supported as compatibility fallbacks.
    """

    if generation_name is not None:
        generation_value = getattr(settings, generation_name, None)
        if generation_value is not None:
            return str(generation_value).strip()

    managed_value = getattr(settings, managed_name, None)
    if managed_value is not None:
        return str(managed_value).strip()

    default_value = getattr(settings, default_name, default)
    if default_value is None:
        return ""

    return str(default_value).strip()


def _validate_provider(provider: str, feature_name: str) -> None:
    if not provider:
        raise RuntimeError(f"Provider is not configured for {feature_name}.")

    if provider.lower() != "openai":
        raise RuntimeError(f"Only OpenAI is supported for {feature_name}.")


def _validate_key(api_key: str, feature_name: str) -> None:
    if not api_key:
        raise RuntimeError(f"OpenAI API key is not configured for {feature_name}.")


def _validate_model(model: str, feature_name: str) -> None:
    if not model:
        raise RuntimeError(f"OpenAI model is not configured for {feature_name}.")


def resolve_generation_config() -> ManagedGenerationConfig:
    provider = _get_server_value(
        generation_name="GENERATION_PROVIDER",
        managed_name="MANAGED_PROVIDER",
        default_name="IMAGE_PROVIDER",
        default="openai",
    ).lower()

    api_key = _get_server_value(
        generation_name="GENERATION_API_KEY",
        managed_name="MANAGED_API_KEY",
        default_name="OPENAI_API_KEY",
    )

    model = _get_server_value(
        generation_name="GENERATION_MODEL",
        managed_name="MANAGED_MODEL",
        default_name="OPENAI_IMAGE_MODEL",
        default="gpt-image-2",
    )

    _validate_provider(provider, "image generation")
    _validate_key(api_key, "image generation")
    _validate_model(model, "image generation")

    return ManagedGenerationConfig(
        provider="openai",
        api_key=api_key,
        model=model,
    )


def resolve_caption_config() -> ManagedGenerationConfig:
    provider = _get_server_value(
        generation_name="GENERATION_PROVIDER",
        managed_name="MANAGED_PROVIDER",
        default_name="TEXT_PROVIDER",
        default="openai",
    ).lower()

    api_key = _get_server_value(
        generation_name="GENERATION_API_KEY",
        managed_name="MANAGED_API_KEY",
        default_name="OPENAI_API_KEY",
    )

    # GENERATION_MODEL is image-specific; captions retain their text model.
    model = _get_server_value(
        managed_name="MANAGED_MODEL",
        default_name="OPENAI_TEXT_MODEL",
        default="gpt-4o-mini",
    )

    _validate_provider(provider, "caption generation")
    _validate_key(api_key, "caption generation")
    _validate_model(model, "caption generation")

    return ManagedGenerationConfig(
        provider="openai",
        api_key=api_key,
        model=model,
    )


__all__ = [
    "GenerationConfig",
    "ManagedGenerationConfig",
    "resolve_caption_config",
    "resolve_generation_config",
]

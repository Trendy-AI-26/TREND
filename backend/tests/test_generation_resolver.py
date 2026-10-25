import pytest

from app.config import settings
from app.services.generation_resolver import (
    resolve_caption_config,
    resolve_generation_config,
)


def _set_managed(monkeypatch, *, provider, model, api_key):
    """Configure the server-side values the resolver actually reads.

    Render GENERATION_* names are cleared so these tests exercise the
    MANAGED_* compatibility layer and the legacy settings fallbacks.
    """

    monkeypatch.setattr(settings, "GENERATION_PROVIDER", None)
    monkeypatch.setattr(settings, "GENERATION_MODEL", None)
    monkeypatch.setattr(settings, "GENERATION_API_KEY", None)
    monkeypatch.setattr(settings, "MANAGED_PROVIDER", provider)
    monkeypatch.setattr(settings, "MANAGED_MODEL", model)
    monkeypatch.setattr(settings, "MANAGED_API_KEY", api_key)


@pytest.fixture
def managed_env(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="openai",
        model="gpt-image-2",
        api_key="server-secret-key",
    )


def test_resolver_uses_server_side_configuration(managed_env):
    """The resolver reads provider/model/key from backend settings only."""

    resolved = resolve_generation_config()

    assert resolved.provider == "openai"
    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "server-secret-key"


def test_resolver_rejects_non_openai_provider(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="gemini",
        model="some-model",
        api_key="server-secret-key",
    )

    with pytest.raises(RuntimeError, match="Only OpenAI is supported"):
        resolve_generation_config()


def test_resolver_rejects_missing_server_key(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="openai",
        model="gpt-image-2",
        api_key="",
    )

    with pytest.raises(RuntimeError, match="API key is not configured"):
        resolve_generation_config()


def test_resolver_rejects_missing_model(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="openai",
        model="   ",
        api_key="server-secret-key",
    )

    with pytest.raises(RuntimeError, match="model is not configured"):
        resolve_generation_config()


def test_resolver_trims_whitespace(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="  openai  ",
        model="  gpt-image-2  ",
        api_key="  server-secret-key  ",
    )

    resolved = resolve_generation_config()

    assert resolved.provider == "openai"
    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "server-secret-key"


def test_resolver_rejects_empty_provider(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="",
        model="gpt-image-2",
        api_key="server-secret-key",
    )

    with pytest.raises(RuntimeError, match="Provider is not configured"):
        resolve_generation_config()


def test_resolver_rejects_provider_with_spaces(monkeypatch):
    _set_managed(
        monkeypatch,
        provider="   ",
        model="gpt-image-2",
        api_key="server-secret-key",
    )

    with pytest.raises(RuntimeError):
        resolve_generation_config()


def test_resolver_falls_back_to_primary_settings(monkeypatch):
    """With no GENERATION_* or MANAGED_* override, legacy settings are used."""

    monkeypatch.setattr(settings, "GENERATION_PROVIDER", None)
    monkeypatch.setattr(settings, "GENERATION_MODEL", None)
    monkeypatch.setattr(settings, "GENERATION_API_KEY", None)
    monkeypatch.setattr(settings, "MANAGED_PROVIDER", None)
    monkeypatch.setattr(settings, "MANAGED_MODEL", None)
    monkeypatch.setattr(settings, "MANAGED_API_KEY", None)
    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_MODEL", "gpt-image-2")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "fallback-key")

    resolved = resolve_generation_config()

    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "fallback-key"


def test_resolver_prefers_render_generation_settings(monkeypatch):
    """The exact names configured on Render resolve before legacy names."""

    monkeypatch.setattr(settings, "GENERATION_PROVIDER", "openai")
    monkeypatch.setattr(settings, "GENERATION_MODEL", "gpt-image-2")
    monkeypatch.setattr(settings, "GENERATION_API_KEY", "render-server-key")
    monkeypatch.setattr(settings, "MANAGED_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "MANAGED_MODEL", "legacy-model")
    monkeypatch.setattr(settings, "MANAGED_API_KEY", "legacy-key")

    resolved = resolve_generation_config()

    assert resolved.provider == "openai"
    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "render-server-key"


def test_caption_resolver_uses_text_model(managed_env, monkeypatch):
    """Captions use the text model, images use the image model."""

    monkeypatch.setattr(settings, "MANAGED_PROVIDER", None)
    monkeypatch.setattr(settings, "MANAGED_MODEL", None)
    monkeypatch.setattr(settings, "MANAGED_API_KEY", None)
    monkeypatch.setattr(settings, "TEXT_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "shared-key")

    resolved = resolve_caption_config()

    assert resolved.model == "gpt-4o-mini"
    assert resolved.api_key == "shared-key"


def test_caption_resolver_uses_render_key_but_not_image_model(monkeypatch):
    """Render's shared key works for captions without using the image model."""

    monkeypatch.setattr(settings, "GENERATION_PROVIDER", "openai")
    monkeypatch.setattr(settings, "GENERATION_MODEL", "gpt-image-2")
    monkeypatch.setattr(settings, "GENERATION_API_KEY", "render-server-key")
    monkeypatch.setattr(settings, "MANAGED_PROVIDER", None)
    monkeypatch.setattr(settings, "MANAGED_MODEL", None)
    monkeypatch.setattr(settings, "MANAGED_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_TEXT_MODEL", "gpt-4o-mini")

    resolved = resolve_caption_config()

    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o-mini"
    assert resolved.api_key == "render-server-key"

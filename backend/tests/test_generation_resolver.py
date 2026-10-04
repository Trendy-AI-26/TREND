import pytest

from app.config import settings
from app.services.generation_resolver import resolve_generation_config


@pytest.fixture
def managed_env(monkeypatch):
    """
    تجهيز إعدادات Server-side وهمية للاختبار.

    نستخدم monkeypatch حتى لا نحتاج إلى API key حقيقي،
    وحتى لا تتأثر إعدادات جهاز المطور بعد انتهاء الاختبار.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_PROVIDER",
        "openai",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "gpt-image-2",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "server-secret-key",
    )


def test_resolver_uses_server_side_configuration(managed_env):
    """
    يتأكد أن Resolver يقرأ provider/model/api key
    من إعدادات Backend وليس من Request المستخدم.
    """
    resolved = resolve_generation_config()

    assert resolved.provider == "openai"
    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "server-secret-key"


def test_resolver_rejects_non_openai_provider(monkeypatch):
    """
    المشروع يعتمد OpenAI فقط حاليًا.
    لذلك يجب رفض أي Provider آخر.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_PROVIDER",
        "gemini",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "some-model",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "server-secret-key",
    )

    with pytest.raises(
        RuntimeError,
        match="Only the OpenAI generation provider is supported",
    ):
        resolve_generation_config()


def test_resolver_rejects_missing_server_key(monkeypatch):
    """
    يجب رفض الإعداد إذا لم يوجد API key في Backend.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_PROVIDER",
        "openai",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "gpt-image-2",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "",
    )

    with pytest.raises(
        RuntimeError,
        match="GENERATION_API_KEY is not configured",
    ):
        resolve_generation_config()


def test_resolver_rejects_missing_model(monkeypatch):
    """
    يجب رفض الإعداد إذا كان model فارغًا أو يحتوي مسافات فقط.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_PROVIDER",
        "openai",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "  ",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "server-secret-key",
    )

    with pytest.raises(
        RuntimeError,
        match="GENERATION_MODEL is not configured",
    ):
        resolve_generation_config()


def test_resolver_trims_whitespace(managed_env, monkeypatch):
    """
    يتأكد أن Resolver ينظف المسافات الزائدة
    من model وAPI key.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "  gpt-image-2  ",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "  server-secret-key  ",
    )

    resolved = resolve_generation_config()

    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "server-secret-key"


def test_resolver_rejects_empty_provider(monkeypatch):
    """
    يجب رفض Provider فارغ لأنه غير مدعوم.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_PROVIDER",
        "",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "gpt-image-2",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "server-secret-key",
    )

    with pytest.raises(
        RuntimeError,
        match="Only the OpenAI generation provider is supported",
    ):
        resolve_generation_config()


def test_resolver_rejects_provider_with_spaces(monkeypatch):
    """
    إذا كانت القيمة تحتوي مسافات فقط،
    يجب أن يفشل الاختبار بدل اعتبارها Provider صالحًا.
    """
    monkeypatch.setattr(
        settings,
        "GENERATION_PROVIDER",
        "   ",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_MODEL",
        "gpt-image-2",
    )
    monkeypatch.setattr(
        settings,
        "GENERATION_API_KEY",
        "server-secret-key",
    )

    with pytest.raises(
        RuntimeError,
        match="Only the OpenAI generation provider is supported",
    ):
        resolve_generation_config()

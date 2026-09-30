"""Server-side resolution of image-generation credentials.

Security contract for this module:

* The provider, model, and API key come from environment configuration ONLY.
* Nothing here accepts input from a request body, query string, or header.
* `GenerateRequest` sets "extra": "forbid", so a browser that tries to send
  `api_key`, `provider`, or `model` is rejected with a 422 before the request
  ever reaches a router.

This is the single place where the key is read, so there is exactly one place
to audit.
"""

from dataclasses import dataclass

from app.config import settings


SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class ManagedGenerationConfig:
    provider: str
    model: str
    api_key: str


def resolve_generation_config() -> ManagedGenerationConfig:
    """Return the managed generation credentials, or raise if unconfigured.

    Raises:
        RuntimeError: if the provider is unsupported, or the model or API key
            is missing from the environment.
    """

    provider = settings.GENERATION_PROVIDER.strip().lower()
    model = settings.GENERATION_MODEL.strip()
    api_key = settings.GENERATION_API_KEY.strip()

    if provider != SUPPORTED_PROVIDER:
        raise RuntimeError("Only the OpenAI generation provider is supported.")

    if not model:
        raise RuntimeError("GENERATION_MODEL is not configured.")

    if not api_key:
        raise RuntimeError("GENERATION_API_KEY is not configured.")

    return ManagedGenerationConfig(
        provider=provider,
        model=model,
        api_key=api_key,
    )

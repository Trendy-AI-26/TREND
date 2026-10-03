from dataclasses import dataclass


@dataclass
class ProviderResult:
    image_bytes: bytes
    request_id: str | None


@dataclass
class ReferenceImage:
    content: bytes
    mime_type: str

class ProviderError(Exception):
    def __init__(self, code: str, user_message: str):
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message





from uuid import uuid4

from app.services import usage


class FakeQuery:
    def __init__(self, client):
        self.client = client

    def insert(self, payload):
        self.client.inserted.append(payload)
        return self

    def update(self, payload):
        self.client.updated.append(payload)
        return self

    def eq(self, *_args):
        return self

    def execute(self):
        return type(
            "Response",
            (),
            {
                "data": [
                    {"id": "usage-1"}
                ]
            },
        )()


class FakeClient:
    def __init__(self):
        self.inserted = []
        self.updated = []

    def table(self, _name):
        return FakeQuery(self)


def test_usage_timer_records_success(monkeypatch):
    fake = FakeClient()

    monkeypatch.setattr(
        usage,
        "get_service_client",
        lambda: fake,
    )

    timer = usage.UsageTimer(
        user_id="user-1",
        generation_id=uuid4(),
        feature="image_generation",
        provider="openai",
        model="gpt-image-2",
        credits=1,
    )

    timer.start()
    timer.finish(
        status="succeeded",
        provider_request_id="request-1",
    )

    assert len(fake.inserted) == 1
    assert fake.inserted[0]["status"] == "started"

    assert len(fake.updated) == 1
    assert fake.updated[0]["status"] == "succeeded"
    assert fake.updated[0]["provider_request_id"] == "request-1"

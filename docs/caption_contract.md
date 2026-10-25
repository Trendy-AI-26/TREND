# Caption Generation Contract — S3-13

S3-13 defines the validated request and response boundary for caption
generation.

It does not call a text provider, persist captions, or expose an HTTP endpoint
yet. Those concerns belong to the following implementation stories.

## Context inheritance

The caption request is scoped to an existing generation. The backend inherits
the generation language, platform preset, image, brief, prompt, and brand
context from the referenced `generation_id`. The client must not resend or
override generation-level context. The user only clicks the caption action;
caption-specific preferences are optional and may be omitted entirely.

Regenerating a caption repeats the same request for the same generation. It
must never change the generation ID or image URL.

## Request

The request contains only optional caption-specific preferences:

```json
{
  "preferences": {
    "tone": "friendly",
    "include_cta": true,
    "include_emojis": false,
    "max_hashtags": 5,
    "extra_notes": "ركز على العرض الحالي"
  }
}
```

An empty request is valid because the generation and questionnaire already
provide the required context:

```json
{}
```

`language`, `platform_preset`, image details, brief details, and brand context
are intentionally not accepted in this request. They are inherited by the
backend from the referenced generation.

## Response

The response is validated as structured data:

```json
{
  "caption": "اكتشفوا تشكيلتنا الجديدة الآن.",
  "hook": "التفاصيل التي تصنع الفرق.",
  "hashtags": ["#عطور", "#عروض"],
  "keywords": ["عطور", "عروض عطور"],
  "trend_used": false,
  "language": "ar"
}
```

`language` is the language inherited from the generation. While Trends are
paused, `trend_used` must be `false`; the service must not accept a model
output that claims a trend was used. The service also enforces the requested
`max_hashtags` preference and checks that keywords and hashtags are naturally
relevant rather than keyword stuffing.

## Validation rules

- `caption` is required and bounded to 2,200 characters.
- `hook` is nullable and bounded to 120 characters.
- `hashtags` is a separate array with at most 8 unique values.
- Each hashtag starts with `#`, contains no whitespace, and is at most 50
  characters.
- `keywords` is a separate array with at most 10 unique values.
- Keywords must not start with `#` or be empty.
- `trend_used` must be a real Boolean.
- Unknown request and response fields are rejected.
- The S3-14 service must verify that the response language matches the
  inherited generation language.

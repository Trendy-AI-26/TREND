# Sprint 4 Contracts

## Beta Rules

- Plan: beta
- Image credits: 3 per period
- Image generation cost: 1 credit
- First caption: included with successful image generation
- Payment: disabled in Sprint 4
- Provider and model: openai
- BYOK: disabled in the public user flow

## Generation Request

The public generation request must not contain:

- api_key
- provider
- model
- vault_secret_id

Example:

{
  "brief": {},
  "platform_preset": "instagram_post",
  "logo_mode": "none"
}

## Generation Flow

1. Authenticate user.
2. Verify brand ownership.
3. Validate brief.
4. Resolve managed provider on the server.
5. Create generation ID.
6. Reserve one credit.
7. Call image provider.
8. Upload image to Storage.
9. Consume credit on success.
10. Release credit on failure.
11. Record usage.
12. Return safe response.

## Error Response

{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "No image credits remain.",
    "request_id": "..."
  }
}

## Required Error Codes

- INSUFFICIENT_CREDITS
- GENERATION_IN_PROGRESS
- RATE_LIMITED
- PROVIDER_TIMEOUT
- PROVIDER_AUTH_FAILED
- PROVIDER_QUOTA_EXCEEDED
- STORAGE_UPLOAD_FAILED
- CAPTION_PROVIDER_ERROR
- BYOK_DISABLED

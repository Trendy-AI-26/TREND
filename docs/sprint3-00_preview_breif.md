S3-00 — Sprint 2 Contracts and Render Tree Audit

Status: Audit completed. The main preview implementation already exists in the current codebase; no new FastAPI endpoint is required for this task.

Backend preview endpoint: POST /brands/{brand_id}/preview-brief

The endpoint is implemented in: backend/app/routers/preview.py

It receives brief and platform_preset, validates the brief through the GenerationBrief Pydantic model, verifies brand ownership, loads the completed Brand Kit when available, and calls build_creative_direction.

The input contract is defined in: backend/app/models/generation.py

The contract includes campaign goal, content type, nested target audience, core idea, voice tone, optional notes, and text to include. Arabic user-authored text is preserved and is not automatically translated.

The transformation service is implemented in: backend/app/services/brief_preview.py

This service maps structured values such as product_launch into readable instructions, formats the target audience, preserves the core idea, and returns a structured creative_direction object. It does not call Gemini or OpenAI and does not generate an image.

The preview router is registered in: backend/app/main.py through app.include_router(preview.router).

Request count: There is one preview POST request for each invocation of fetchPreview. The request may run again when the brief or platform changes while the user is on the Summary step. There is no independent request inside BriefCreativePreview.
The preview endpoint is separate from the actual image-generation endpoint:
POST /brands/{brand_id}/preview-brief

only prepares a creative direction, while:
POST /brands/{brand_id}/generate
is responsible for the actual AI image generation.

Desktop and mobile behavior:
The application uses one responsive render tree. It does not render separate desktop and mobile preview components. CSS changes the layout at responsive breakpoints: the generation form becomes a two-column layout on large screens, while the same content becomes a single-column layout on smaller screens. The preview is not duplicated and should not be hidden with CSS as a workaround

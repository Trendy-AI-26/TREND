# S3-00 — Preview Brief audit

**Date:** 2026-09-03

## Findings

The canonical review flow is owned by `frontend/components/generation/generation-brief-form.tsx`. When `step === 5`, that component renders exactly one `BriefCreativePreview` and one `BriefSummary`. `frontend/components/generation/generator-form.tsx` mounts exactly one `GenerationBriefForm`; it does not render a second preview. A repository-wide search found no other `BriefCreativePreview` usage.

`BriefCreativePreview` itself renders one root card after the preview response succeeds. Its loading and error branches also render one root state each. `BriefSummary` is a separate editable input summary titled “Review your brief”; it is not another `BriefCreativePreview`, but it can look like a second brief summary to a user because both are displayed in the Summary step.

The preview request is initiated by the top-level effect in `GenerationBriefForm` when `step === 5`, the brief is complete, and `platformPreset` exists. The request flows through `usePreviewBrief` to `POST /brands/{brand_id}/preview-brief`, then through the Next.js proxy route to the FastAPI preview router. Before this change, the hook had no request identity, deduplication, cancellation, or stale-response protection.

## Decision

Keep one canonical `BriefCreativePreview` instance in the existing parent review step. Do not hide a duplicate with CSS. Harden `usePreviewBrief` with a stable request key composed of `brandId`, `platformPreset`, and the serialized structured brief. Identical effect replays are ignored, a previous request is aborted when the brief changes, and only the active request may update preview/loading/error state.

The current codebase has no frontend test runner configured. S3-02 should add the project’s chosen component/browser test setup or use the existing team verification approach to assert one preview heading/card and one request for a stable brief.

## Files reviewed

| Area | File |
| --- | --- |
| Review parent | `frontend/components/generation/generation-brief-form.tsx` |
| Canonical preview | `frontend/components/generation/brief-creative-preview.tsx` |
| Request hook | `frontend/hooks/use-preview-brief.ts` |
| Generation parent | `frontend/components/generation/generator-form.tsx` |
| Frontend proxy | `frontend/app/api/brands/[brandId]/preview-brief/route.ts` |
| Backend endpoint | `backend/app/routers/preview.py` |
| Brief contract | `frontend/types/generation.ts`, `backend/app/models/generation.py` |
| Prompt contract | `backend/app/services/prompt_composer.py` |

## Verification completed

The frontend passes `npm run lint` and `npm run build`. The backend suite passes with **148 tests passed**. A dedicated frontend DOM/browser regression test is not yet present because the frontend package does not currently configure a component test runner; that remains the explicit S3-02 follow-up. The implementation does expose `data-testid="brief-creative-preview"` on the single preview root and makes retry use the same hook instance.

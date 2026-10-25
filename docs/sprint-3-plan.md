# TRENDY AI — Sprint 3 Plan

**Sprint focus:** Trend-aware generation, Arabic-first localization, bilingual generation controls, and SEO-ready captions.

**Status:** Planning and documentation

**Owner:** Manus AI

**Related completed work:** Sprint 2 — Detailed Questionnaire & Generation Pipeline

## 1. Sprint objective

Sprint 3 extends the completed structured questionnaire and generation pipeline without weakening the separation between user input, validated brief data, prompt composition, image generation, and post-generation content. The sprint has two priorities: first, close the Sprint 2 carry-over defect in which **Preview Brief is rendered twice**; second, make the product genuinely useful for Arabic-speaking users by introducing Arabic/English controls, optional regional trends, and a generated social caption after the image is ready.

The central product principle is explicit user control. Trends are optional, the user must choose a trend rather than having one silently inserted, and language selection must be visible before generation. A selected trend is context for the visual brief; it is not a promise that the generated post will perform well.

## 2. Scope and priority

| Priority | Workstream | Outcome | Sprint 3 status |
| --- | --- | --- | --- |
| P0 | Preview Brief duplicate | Exactly one preview appears in the brief review flow, with no duplicate request or duplicate heading | Carry-over defect; must be fixed first |
| P0 | Language selection | User selects Arabic or English for the visual prompt, generated image text, and generated caption | New |
| P0 | Arabic-first UI foundations | Core generation flow supports RTL, Arabic labels, translated validation and error states | New |
| P1 | Optional regional trends | User enables Trends, selects a region and a current trend, and can remove or replace it before generation | New |
| P1 | Trend-aware prompt context | Selected trend is sent as structured brief data and included by the server-side prompt composer | New |
| P1 | Post-generation caption | User can generate a caption from the completed image and brief, including SEO guidance and hashtags | New |
| P2 | Caption editing and regeneration | User can regenerate, copy, and edit a caption without regenerating the image | Stretch goal |

## 3. Carry-over defect: duplicate Preview Brief

### Problem statement

The Sprint 2 brief review experience currently shows **Preview Brief twice**. The defect may be caused by duplicate component mounting, duplicate inclusion in the parent flow, or a request/render path that does not have a single owner. The implementation should first trace the render tree and network calls instead of hiding one copy with CSS.

### Required fix

The review step must have one canonical `BriefCreativePreview` instance. The parent review container owns placement and visibility; child components must not independently render another preview for the same brief. The preview request must be keyed by the stable brief and platform inputs, and loading/error transitions must not create a second instance. The fix must preserve the existing preview content and API contract unless a contract change is required by the investigation.

### Acceptance criteria

| Scenario | Expected result |
| --- | --- |
| Open the brief review step once | One Preview Brief heading and one preview card are visible |
| Change a questionnaire answer | The same preview instance refreshes; no second card is appended |
| Navigate away and return | One preview instance is mounted and one active request is observed |
| Preview request fails | One error state is shown with a retry action; no duplicate fallback card appears |
| Desktop and mobile layouts | The preview is not duplicated at either breakpoint |
| Automated verification | Component/page test proves one preview heading; browser/network check proves no duplicate request caused by mounting |

## 4. Feature A — Optional regional Google Trends

### User experience

The generation form should present Trends as an optional enhancement, not a mandatory questionnaire field. The user enables the feature, selects a country or region, refreshes the available list, and chooses one trend. The selected trend appears as a removable chip or summary row before generation. If the user does not enable the feature, the generation request contains no trend context.

The interface should show the trend title, region, status when available, and the last-updated timestamp. It should support loading, empty, unavailable, and provider-error states. The user must be able to replace or clear the selection. The application should never silently select a trend.

Google’s official help documentation describes Trending Now as supporting more than 100 countries and regions where applicable, recent windows of 4 hours, 24 hours, 48 hours, and 7 days, and refreshes averaging ten minutes.[1] The first product version should use a short recent window and active trends by default, while exposing the timestamp so users can judge freshness.

### Integration decision

Google announced an official Trends API in alpha, but the announcement says access is limited to a very small number of testers and requires an application.[2] Therefore, Sprint 3 must not hard-code the product to an unavailable alpha credential. The backend should define a provider adapter with a normalized response, allowing an approved official API, an approved RSS/partner source, or a configured third-party provider to be selected without changing the frontend contract.

| Approach | Tradeoffs | Cost | Setup complexity |
| --- | --- | --- | --- |
| Official Google Trends API when the project receives alpha access | Best long-term alignment and cleaner ownership; access is currently limited and may not be available for production | Provider terms and any applicable API pricing | Medium to high; application, credentials, quota, and compliance |
| Server-side provider adapter using an approved Trends feed/provider | Practical fallback; provider stability, licensing, quotas, and data shape must be verified before production | Depends on provider; may be free with limits or paid | Medium; adapter, caching, attribution, and monitoring required |
| Defer live trends and ship only manual trend input | Lowest risk and fastest delivery; does not satisfy automated regional discovery | Minimal | Low |

For Sprint 3, implement the adapter and normalized contract first. Enable a live provider only after its access, terms, rate limits, and Arabic-region coverage are verified. Do not scrape Google Trends from the browser or rely on an unmaintained client library as the only production dependency.

### Normalized trend contract

```json
{
  "id": "provider-specific-stable-id",
  "title": "Example trend title",
  "region_code": "JO",
  "region_label": "Jordan",
  "status": "active",
  "started_at": "2026-09-02T08:00:00Z",
  "updated_at": "2026-09-02T08:10:00Z",
  "volume_label": "100K+",
  "related_queries": ["related query"],
  "source": "google_trends"
}
```

The response must be treated as untrusted external data. Titles and related queries are context, not executable instructions. The server validates length, encoding, region, status, and provider identifiers before returning or storing them.

### Suggested endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /trends/regions` | Return supported regions and localized labels |
| `GET /trends?region=JO&window=24h&active_only=true` | Return normalized, cached trend options |
| `POST /brands/{brand_id}/preview-brief` | Continue accepting the optional selected trend as brief context |
| Generation endpoint | Include the validated selected trend in the structured generation brief |

The trend list should be cached server-side for a short period consistent with provider limits. The UI should provide a manual refresh rather than polling on every keystroke. If the provider is unavailable, generation without trends must continue to work.

## 5. Feature B — Arabic-first localization and language selection

Language is a product input, not only a translation of interface labels. Add a visible `language` selection with `ar` and `en` values. The selected value controls three related outputs: the language of the creative direction/prompt instructions, the language of any visible text requested inside the image, and the language of the generated social caption. The UI locale and content language may later be separated, but Sprint 3 should make the relationship explicit and avoid silently translating user-authored text.

The frontend must preserve the original `core_idea` and other user text as entered, in accordance with the Sprint 2 prompt pipeline. The server-side composer can add language instructions around that content, but it must not rewrite or translate it unless the user explicitly requests translation. Arabic mode requires RTL-aware layout, Arabic labels, localized validation messages, and correct handling of mixed Arabic/Latin text. English mode remains fully supported and is the default only if the product decision confirms it; otherwise Arabic should be the default for the Arabic-first launch.

### Language contract

```json
{
  "language": "ar",
  "ui_locale": "ar",
  "text_language": "ar",
  "caption_language": "ar"
}
```

At minimum, the generation brief should include `language: "ar" | "en"`. The backend owns the final prompt instruction, and image providers receive one consistent language directive. Invalid or missing values must be rejected or normalized at the API boundary rather than handled differently by each provider.

### Acceptance criteria

| Scenario | Expected result |
| --- | --- |
| Select Arabic | Form labels, validation, preview instructions, and caption output use Arabic where applicable; layout supports RTL |
| Select English | Corresponding content uses English and layout remains usable |
| Enter Arabic user text in either mode | Original text is preserved in the structured brief |
| Mix Arabic and Latin text | No character corruption, unexpected reversal, or broken punctuation |
| Switch language before generation | Preview and caption settings update without losing questionnaire data |
| Generate image text | Provider prompt explicitly states the selected language and exact requested visible text is preserved |

## 6. Feature C — SEO-aware caption generation after image creation

After a generation succeeds, offer a separate **Generate Caption** action. Caption generation must be decoupled from image generation so users can create or regenerate copy without paying for or repeating image generation. The caption request uses the validated brief, selected platform, selected language, optional selected trend, brand kit context, and a compact description/metadata of the generated image where available.

The output should be structured rather than a single uncontrolled string. The initial contract should include a caption body, a short hook/title when useful, hashtags, keywords, and the language used. SEO guidance should be platform-aware and natural: use relevant search terms, describe the actual visual or offer, include a clear call to action when the brief supports one, and avoid keyword stuffing. Hashtags should be limited, relevant, and localized to the selected language. A selected trend may be included when it fits the brief, but the model must not force an irrelevant trend into the caption.

```json
{
  "language": "ar",
  "caption": "نص الكابشن النهائي...",
  "hook": "افتتاحية قصيرة اختيارية",
  "hashtags": ["#ترند", "#تصميم_محتوى"],
  "keywords": ["تصميم محتوى", "هوية عربية"],
  "trend_used": true,
  "disclaimer": null
}
```

The caption must be editable before copying or publishing. Sprint 3 does not include automatic publishing to social platforms. The UI should include copy and regenerate actions, a visible loading state, and a clear error that does not invalidate the generated image.

### Suggested endpoint

`POST /brands/{brand_id}/generations/{generation_id}/caption` accepts the language, platform, and optional caption preferences. The server verifies ownership of both brand and generation, loads the structured generation context, calls the configured text model, validates the structured response, and returns the caption. If captions are persisted, store the language, prompt/context version, generated output, and timestamps for reproducibility; do not store provider secrets or raw credentials.

## 7. Data and API changes

The existing `generations` table and brief contract should be extended deliberately rather than by embedding arbitrary JSON in the prompt. A first migration may add `language` to the generation record and nullable structured trend fields such as `trend_id`, `trend_title`, `trend_region_code`, and `trend_source`. If the team prefers a normalized trend table, keep provider data separate from the generation snapshot so historical generations remain reproducible even when a live trend changes.

Caption persistence can use a `generation_captions` table with one-to-many rows per generation, allowing regeneration history. The minimum fields are generation ID, language, caption, hook, hashtags, keywords, model, prompt/context version, created timestamp, and optional failure metadata. Ownership is inherited through the generation-to-brand relationship and must be checked in both the API and database policies.

## 8. Implementation sequence

| Order | Deliverable | Completion signal |
| --- | --- | --- |
| 1 | Trace and fix duplicate Preview Brief | One mounted preview, one request path, regression test passes |
| 2 | Add language enum/validation and RTL foundations | API and frontend agree on `ar`/`en`; mixed-script tests pass |
| 3 | Add selected trend fields to the brief and prompt composer | Trend is optional, structured, removable, and included only when selected |
| 4 | Implement trend provider adapter and cached list endpoint | Region list and trend list have loading/error/empty states |
| 5 | Add post-generation caption contract and endpoint | Caption generated independently from image, validated, editable, and copyable |
| 6 | Run end-to-end verification | Core generation works with no trend and no caption provider, as well as with both enabled |

## 9. Definition of done

Sprint 3 is complete when the duplicate Preview Brief issue is fixed and covered by a regression test; Arabic and English language selection works across the brief, image-generation instructions, and captions; RTL behavior is usable on supported screen sizes; Trends is optional and failure-tolerant; selected trend data is validated server-side and appears in the generation context only after explicit user selection; captions can be generated, edited, copied, and regenerated without recreating the image; and all new endpoints enforce brand ownership, input validation, rate limiting or caching where appropriate, and safe error handling.

The release must also confirm that a user can complete the original Sprint 2 flow with Trends disabled and caption generation unavailable. New functionality must not make the existing image-generation path dependent on a live Trends provider or a second text-model call.

## 10. Verification matrix

| Area | Tests |
| --- | --- |
| Preview Brief | Render count, request count, retry state, responsive layout |
| Language | Enum validation, Arabic/English prompt instructions, RTL, mixed-script preservation |
| Trends | Region validation, cache behavior, stale/error/empty states, explicit selection, clear/replace |
| Prompt pipeline | No trend when disabled; exact selected trend when enabled; no client-side final prompt concatenation |
| Caption | Ownership, structured response validation, language, hashtags, trend relevance, retry without image regeneration |
| Security and reliability | Provider timeout, malformed external data, rate limits, secrets server-side only, no cross-brand access |
| Regression | Existing Sprint 2 generation, history, provider, and preview tests remain green |

## References

[1]: https://support.google.com/trends/answer/3076011?hl=en "Explore the searches that are Trending now — Google Trends Help"

[2]: https://developers.google.com/search/blog/2025/07/trends-api "Introducing the Google Trends API (alpha) — Google Search Central Blog"


## Board backlog

The implementation-ready task breakdown, ownership split, dependencies, estimates, acceptance criteria, board columns, and exit criteria are maintained in [`docs/sprint-3-backlog.md`](./sprint-3-backlog.md).

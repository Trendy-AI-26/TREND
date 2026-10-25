# Internationalization (i18n) and RTL/LTR


## 8. API Error Codes and Frontend Translation

API error responses use a stable machine-readable `error.code` rather than a localized message as the integration contract. The backend returns the error code, the original diagnostic message, and, when available, a `request_id` for tracing. For example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "language must be one of: ar, en",
    "request_id": "..."
  }
}
```

The backend must not select Arabic or English presentation text. It should preserve the appropriate error code for the condition, such as `VALIDATION_ERROR`, `NOT_FOUND`, or a provider-specific error code, and may include the raw message for logs and fallback behavior. The frontend parses the response in `frontend/lib/api.ts`, keeps the code on `ApiError.code`, and is responsible for resolving the user-facing localized message from the active language dictionary.

When adding a new API error, follow this sequence:

1. Add or reuse a stable uppercase error code in the backend response.
2. Keep the code independent of the user-facing language; never use translated text as the code.
3. Add the matching key to both `frontend/public/locales/en.json` and `frontend/public/locales/ar.json`.
4. Render the translated frontend message, while retaining `request_id` for support and debugging.

This separation keeps API behavior stable for clients and allows the frontend to switch between Arabic and English without requiring backend changes.
# Internationalization (i18n) & RTL/LTR Documentation

## 1. Overview & Architecture

The internationalization (i18n) system in **TRENDY AI** provides full bilingual support for **English (`en`)** and **Arabic (`ar`)**, including automatic layout flipping between **LTR (Left-to-Right)** and **RTL (Right-to-Left)**.

### Architectural Highlights
- **Zero Additional Dependencies**: Built directly on React Context and Next.js 14 App Router without third-party libraries (no `next-intl` or `react-i18next`).
- **No Route Mutation**: Avoids route prefixing (`/en/...`, `/ar/...`), preserving existing route structures, Supabase auth redirects, and dashboard routing.
- **Client Persistence**: Persists user choice in `localStorage` under the key `trendy-lang`, instantly restored upon revisit.
- **Dynamic DOM Sync**: Updates `document.documentElement.lang` and `document.documentElement.dir` synchronously.
- **Tailwind v3 Native RTL**: Leverages Tailwind's logical utilities (`start`, `end`, `border-e`, `text-start`) and `rtl:` variants without external CSS plugins.

---

## 2. Directory Structure

```text
frontend/
├── app/
│   ├── layout.tsx                    # Wraps tree in LanguageProvider; loads Arabic font
│   └── globals.css                   # RTL font and LTR input resets
├── lib/
│   └── i18n/
│       ├── LanguageContext.tsx       # React Context provider & useLanguage() hook
│       └── translations.ts           # Safe dot-notation translation resolver
├── public/
│   └── locales/
│       ├── en.json                   # English dictionary
│       └── ar.json                   # Arabic dictionary
└── components/
    ├── Header.tsx                    # Landing page header with language switcher
    ├── layout/
    │   ├── app-shell.tsx             # Responsive dashboard layout (LTR & RTL drawer)
    │   └── app-sidebar.tsx           # Dashboard sidebar with nav translations & toggle
    └── account/
        └── profile-form.tsx          # Account settings with language selection dropdown
```

## 1. Overview

TREND supports English (`en`) and Arabic (`ar`) through [`next-intl`](https://next-intl.dev/). The application uses the same message dictionaries for server and client rendering, and sets the document language and direction from the active locale.

The canonical dictionaries are:

- `frontend/messages/en.json`
- `frontend/messages/ar.json`

`frontend/public/locales` is not used by the current application and must not be treated as a second source of translations.

## 2. Locale resolution

Locale resolution is implemented in `frontend/i18n/request.ts`.

- Supported locales: `ar` and `en`.
- Default locale: `ar` (Arabic-first, as specified for Sprint 3).
- User selection is persisted in the `NEXT_LOCALE` cookie.
- If the cookie is absent or unsupported, the application uses Arabic.
- Messages are loaded from `frontend/messages/{locale}.json`.

The settings language selector writes the cookie and calls `router.refresh()` so the server-rendered messages and document attributes are refreshed.

## 3. Provider and document direction

`frontend/app/layout.tsx` loads the active locale and messages using `next-intl/server`, then wraps the application with `NextIntlClientProvider`.

The root document is rendered with:

```tsx
<html lang={locale} dir={locale === 'ar' ? 'rtl' : 'ltr'}>
```

Therefore:

- English uses `lang="en"` and `dir="ltr"`.
- Arabic uses `lang="ar"` and `dir="rtl"`.

The Arabic font is loaded through `Noto_Naskh_Arabic`. RTL-specific body styling is defined in `frontend/app/globals.css`.

## 4. Using translations in components

Client components should import the hooks from `next-intl`:

```tsx
'use client'

import { useLocale, useTranslations } from 'next-intl'

export function MyComponent() {
  const locale = useLocale()
  const t = useTranslations('mySection')
  const isRTL = locale === 'ar'

  return (
    <section>
      <h1>{t('title')}</h1>
      <p>{t('description')}</p>
      {isRTL && <span>Arabic layout</span>}
    </section>
  )
}
```

Use a component-specific namespace when possible. For example:

```tsx
const t = useTranslations('components.keys.key-card')
```

Then access keys below that namespace with `t('validate')`, `t('delete')`, and so on.

## 5. Adding or changing messages

Every new key must be added to both dictionaries with the same structure:

```json
{
  "mySection": {
    "title": "Welcome",
    "description": "Here is the content"
  }
}
```

The Arabic dictionary must contain the corresponding Arabic values:

```json
{
  "mySection": {
    "title": "مرحبًا",
    "description": "إليك المحتوى"
  }
}
```

Product and provider names such as `OpenAI`, `Gemini`, and `TRENDY AI` may remain unchanged when they are proper names. User-facing actions, status labels, errors, placeholders, and accessibility labels must be translated.

Do not add messages to `frontend/public/locales`; it is not the runtime source.

## 6. RTL implementation rules

Prefer CSS logical properties and Tailwind logical utilities so the same component works in both directions:

- Use `start` and `end` instead of `left` and `right`.
- Use `border-s` and `border-e` instead of directional border classes where appropriate.
- Use `text-start` and `text-end` for text alignment.
- Use `rtl:` variants when an icon or drawer must flip direction.
- Keep email and URL inputs LTR for reliable entry of symbols such as `@`, `.`, and `/`.

The dashboard shell explicitly handles the mobile drawer transition in RTL and LTR. Direction-sensitive changes should be checked at both desktop and mobile breakpoints.

## 7. Testing localized components

A component that calls `useTranslations` must be rendered below `NextIntlClientProvider` in tests:

```tsx
import { NextIntlClientProvider } from 'next-intl'
import messages from '@/messages/en.json'

render(
  <NextIntlClientProvider locale="en" messages={messages}>
    <MyComponent />
  </NextIntlClientProvider>,
)
```

Tests should assert behavior and accessible roles. When an accessible name is translated, use the message for the test locale rather than assuming the English text is always present.

At minimum, localization changes should be checked with:

```bash
cd frontend
npx tsc --noEmit
npm test -- --run
npm run build
```

## 8. Review checklist

Before merging an i18n change, verify that:

1. Both `en.json` and `ar.json` contain the same keys.
2. No user-facing hardcoded English or Arabic text remains in the changed component.
3. Interactive elements have translated accessible labels.
4. Tests provide `NextIntlClientProvider` where required.
5. `lang` and `dir` change correctly when the locale changes.
6. The layout remains usable in both LTR and RTL.
7. The production build and the full test suite pass.

This implementation replaces the former `LanguageContext`/`useLanguage` approach. New code must use `next-intl` rather than the obsolete API described in earlier documentation.

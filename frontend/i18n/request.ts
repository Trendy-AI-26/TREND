import { getRequestConfig } from 'next-intl/server';
import { cookies } from 'next/headers';

// Supported languages for the whole app (UI locale).
// Keep this list in sync with the keys under /messages.
export const SUPPORTED_LOCALES = ['ar', 'en'] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

// Default locale for the product (Arabic-first, per S3-03).
export const DEFAULT_LOCALE: Locale = 'ar';

const COOKIE_NAME = 'NEXT_LOCALE';

export default getRequestConfig(async () => {
    const cookieStore = await cookies();
    const cookieLocale = cookieStore.get(COOKIE_NAME)?.value;

    const locale: Locale = SUPPORTED_LOCALES.includes(cookieLocale as Locale)
        ? (cookieLocale as Locale)
        : DEFAULT_LOCALE;

    return {
        locale,
        messages: (await import(`../messages/${locale}.json`)).default,
    };
});
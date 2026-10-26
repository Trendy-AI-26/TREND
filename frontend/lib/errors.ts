/**
 * Turns a thrown error (usually an `ApiError`) into a translated, user-facing message.
 *
 * `t` is the translator for the `errors` namespace: `useTranslations('errors')`.
 */

type Translate = (key: string) => string

/** Backend `error.code` values that have a translation under `errors.codes`. */
const CODE_KEYS: Record<string, string> = {
  ACCOUNT_DISABLED: 'codes.ACCOUNT_DISABLED',
  ADMIN_TARGET_FORBIDDEN: 'codes.ADMIN_TARGET_FORBIDDEN',
  USER_NOT_FOUND: 'codes.USER_NOT_FOUND',
  TREND_NOT_FOUND: 'codes.TREND_NOT_FOUND',
  TREND_SLUG_TAKEN: 'codes.TREND_SLUG_TAKEN',
  TREND_IN_USE: 'codes.TREND_IN_USE',
  VALIDATION_ERROR: 'codes.VALIDATION_ERROR',
  DATA_CONSTRAINT_VIOLATION: 'codes.DATA_CONSTRAINT_VIOLATION',
  BRAND_NOT_FOUND: 'codes.BRAND_NOT_FOUND',
  BRAND_LIMIT_REACHED: 'codes.BRAND_LIMIT_REACHED',
  DUPLICATE_BRAND_NAME: 'codes.DUPLICATE_BRAND_NAME',
  LOGO_REQUIRED: 'codes.LOGO_REQUIRED',
  PRODUCT_ASSET_REQUIRED: 'codes.PRODUCT_ASSET_REQUIRED',
  PRODUCT_ASSET_NOT_FOUND: 'codes.PRODUCT_ASSET_NOT_FOUND',
  RATE_LIMITED: 'codes.RATE_LIMITED',
  GENERATION_IN_PROGRESS: 'codes.GENERATION_IN_PROGRESS',
  GENERATION_SETTLEMENT_PENDING: 'codes.GENERATION_SETTLEMENT_PENDING',
  GENERATION_OUTCOME_UNKNOWN: 'codes.GENERATION_OUTCOME_UNKNOWN',
  // Client-side: the inputs changed while a request with another payload is unresolved.
  GENERATION_INTENT_UNRESOLVED: 'codes.GENERATION_INTENT_UNRESOLVED',
  GENERATION_LIMIT_REACHED: 'codes.GENERATION_LIMIT_REACHED',
  DAILY_GENERATION_LIMIT_REACHED: 'codes.DAILY_GENERATION_LIMIT_REACHED',
  TRIAL_EXPIRED: 'codes.TRIAL_EXPIRED',
  GENERATION_CONFIGURATION_ERROR: 'codes.GENERATION_CONFIGURATION_ERROR',
  TIMEOUT: 'codes.TIMEOUT',
  GATEWAY_TIMEOUT: 'codes.TIMEOUT',
  BACKEND_UNREACHABLE: 'codes.BACKEND_UNREACHABLE',
  STORAGE_DELETE_FAILED: 'codes.STORAGE_DELETE_FAILED',
  INTERNAL_ERROR: 'codes.INTERNAL_ERROR',
  // Common failures of the upload / generation actions.
  FILE_TOO_LARGE: 'codes.FILE_TOO_LARGE',
  PRODUCT_ASSET_TOO_LARGE: 'codes.FILE_TOO_LARGE',
  AVATAR_TOO_LARGE: 'codes.FILE_TOO_LARGE',
  INVALID_FILE_TYPE: 'codes.INVALID_FILE_TYPE',
  UNSUPPORTED_IMAGE_TYPE: 'codes.INVALID_FILE_TYPE',
  INVALID_AVATAR_TYPE: 'codes.INVALID_FILE_TYPE',
  INVALID_IMAGE: 'codes.INVALID_IMAGE',
  CONTENT_POLICY: 'codes.CONTENT_POLICY',
  GENERATION_NOT_FOUND: 'codes.GENERATION_NOT_FOUND',
  FORBIDDEN: 'codes.FORBIDDEN',
  UNAUTHORIZED: 'codes.UNAUTHORIZED',
  // Client-side: apiRequest() could not reach the server at all.
  NETWORK_ERROR: 'network',
}

/** Codes that never come from a backend error payload. */
const NON_BACKEND_CODES = new Set(['UNKNOWN', 'NETWORK_ERROR'])

interface ErrorFields {
  code?: string
  status?: number
  message?: string
}

function readFields(err: unknown): ErrorFields {
  if (!err || typeof err !== 'object') return {}
  const { code, status, message } = err as Record<string, unknown>
  return {
    code: typeof code === 'string' ? code : undefined,
    status: typeof status === 'number' ? status : undefined,
    message: typeof message === 'string' ? message : undefined,
  }
}

/** True when the error means "no response from the server". */
function isNetworkFailure(err: unknown, fields: ErrorFields): boolean {
  if (fields.status === 0) return true
  return err instanceof TypeError
}

export function errorMessage(err: unknown, t: Translate): string {
  const fields = readFields(err)

  // 1. A known backend code always wins.
  if (fields.code && CODE_KEYS[fields.code]) {
    return t(CODE_KEYS[fields.code])
  }

  // 2. Unknown code: fall back by HTTP status.
  if (isNetworkFailure(err, fields)) return t('network')
  if (fields.status !== undefined && fields.status >= 500) return t('generic')

  // 3. Last resort: a clear backend message, only for 4xx with an unknown code.
  if (
    fields.status !== undefined &&
    fields.status >= 400 &&
    fields.status < 500 &&
    fields.code &&
    !NON_BACKEND_CODES.has(fields.code) &&
    fields.message &&
    fields.message.trim()
  ) {
    return fields.message
  }

  return t('generic')
}

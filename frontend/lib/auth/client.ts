import { apiRequest, ApiError } from '@/lib/api'
import type { AuthUser } from './session'

export type { AuthUser } from './session'
export { logout } from '@/lib/api'

export type CodePurpose = 'verify_email' | 'reset_password'

/** sessionStorage key holding the `reset_token` between verify-code and reset-password. */
export const RESET_TOKEN_KEY = 'trendy_reset_token'

export function parsePurpose(value: string | null | undefined): CodePurpose {
  return value === 'reset_password' ? 'reset_password' : 'verify_email'
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(`/auth${path}`, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
    // A 401 here (e.g. INVALID_CREDENTIALS) is an error to show, not a session expiry.
    redirectOn401: false,
  })
}

export const authApi = {
  signup: (input: { email: string; password: string; full_name?: string }) =>
    post<{ email: string; verification_required: boolean }>('/signup', input),
  verifyEmail: (input: { email: string; code: string }) =>
    post<{ user: AuthUser }>('/verify-email', input),
  resendCode: (input: { email: string; purpose: CodePurpose }) =>
    post<{ sent: boolean }>('/resend-code', input),
  login: (input: { email: string; password: string }) =>
    post<{ user: AuthUser }>('/login', input),
  forgotPassword: (input: { email: string }) =>
    post<{ sent: boolean }>('/forgot-password', input),
  verifyResetCode: (input: { email: string; code: string }) =>
    post<{ reset_token: string }>('/verify-reset-code', input),
  resetPassword: (input: { reset_token: string; password: string }) =>
    post<{ ok: boolean }>('/reset-password', input),
}

/** Backend error codes that have a translation under the `auth` namespace. */
const ERROR_CODE_KEYS: Record<string, string> = {
  INVALID_CREDENTIALS: 'errorInvalidCredentials',
  EMAIL_ALREADY_REGISTERED: 'existingAccount',
  EMAIL_NOT_VERIFIED: 'errorEmailNotVerified',
  INVALID_CODE: 'errorInvalidCode',
  CODE_EXPIRED: 'errorCodeExpired',
  TOO_MANY_ATTEMPTS: 'errorTooManyAttempts',
  INVALID_RESET_TOKEN: 'errorInvalidResetToken',
}

/**
 * Turns a thrown error into a user-facing message: a translation when the
 * backend code is known, otherwise the backend's own message.
 */
export function authErrorMessage(err: unknown, t: (key: string) => string): string {
  if (err instanceof ApiError) {
    const key = ERROR_CODE_KEYS[err.code]
    return key ? t(key) : err.message
  }
  return err instanceof Error ? err.message : t('errorGeneric')
}

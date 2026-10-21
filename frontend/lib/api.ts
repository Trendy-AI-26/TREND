export class ApiError extends Error {
  code: string
  requestId?: string

  constructor(message: string, code: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.requestId = requestId
  }
}

function parseErrorPayload(
  payload: unknown,
): { code: string; message: string; requestId?: string } | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }

  const errorPayload = payload as {
    error?: { code?: unknown; message?: unknown; request_id?: unknown }
    detail?: unknown
  }

  if (errorPayload.error && typeof errorPayload.error.message === 'string') {
    return {
      code:
        typeof errorPayload.error.code === 'string'
          ? errorPayload.error.code
          : 'UNKNOWN',
      message: errorPayload.error.message,
      requestId:
        typeof errorPayload.error.request_id === 'string'
          ? errorPayload.error.request_id
          : undefined,
    }
  }

  if (typeof errorPayload.detail === 'string') {
    return { code: 'VALIDATION_ERROR', message: errorPayload.detail }
  }

  if (Array.isArray(errorPayload.detail)) {
    const firstMessage = errorPayload.detail.find(
      (item): item is { msg?: string } =>
        Boolean(item) && typeof item === 'object' && 'msg' in item
    )
    if (typeof firstMessage?.msg === 'string') {
      return { code: 'VALIDATION_ERROR', message: firstMessage.msg }
    }
  }

  return null
}

function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL || '/api'
}

/**
 * Asks the backend to clear the httpOnly session cookie. Failures are ignored:
 * the caller is leaving the authenticated area either way.
 */
export async function logout(): Promise<void> {
  try {
    await fetch(`${getApiBase()}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } catch {
    // ignore
  }
}

export interface ApiRequestOptions extends RequestInit {
  /**
   * On HTTP 401, log out and go to /login (default). Auth endpoints such as
   * `/auth/login` set this to false: their 401 is a normal error to display.
   */
  redirectOn401?: boolean
}

export async function apiRequest<T = unknown>(
  endpoint: string,
  { redirectOn401 = true, ...options }: ApiRequestOptions = {}
): Promise<T> {
  const headers = new Headers(options.headers)

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  // The session is an httpOnly cookie set by the backend; no token handling here.
  const response = await fetch(`${getApiBase()}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && redirectOn401) {
    if (typeof window !== 'undefined') {
      await logout()
      window.location.href = '/login'
    }
    throw new ApiError('Unauthorized', 'UNAUTHORIZED')
  }

  if (!response.ok) {
    let message = response.statusText || 'API request failed'
    let code = 'UNKNOWN'
    let requestId: string | undefined
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      try {
        const text = await response.text()
        const parsed = parseErrorPayload(JSON.parse(text))
        if (parsed) {
          message = parsed.message
          code = parsed.code
          requestId = parsed.requestId
        }
      } catch {
        // JSON parse failed, use default message
      }
    }
    throw new ApiError(message, code, requestId)
  }

  if (
    response.status === 204 ||
    response.headers.get('content-length') === '0' ||
    !response.headers.get('content-type')?.includes('application/json')
  ) {
    return null as T
  }

  return response.json()
}

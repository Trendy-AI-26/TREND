import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from '@/lib/api'

const fetchMock = vi.fn()

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

// jsdom's location is non-configurable; stub window rather than redefining it.
function stubLocation() {
  const stub = { href: 'http://localhost/dashboard' }
  vi.stubGlobal('window', { location: stub })
  return stub
}

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiRequest', () => {
  it('sends the session cookie (credentials: include) and no Authorization header', async () => {
    fetchMock.mockResolvedValueOnce(json({ ok: true }))

    await expect(apiRequest('/me')).resolves.toEqual({ ok: true })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/me')
    expect(init.credentials).toBe('include')
    expect(new Headers(init.headers).has('Authorization')).toBe(false)
  })

  it('on 401 calls POST /api/auth/logout, goes to /login and throws', async () => {
    const location = stubLocation()
    fetchMock
      .mockResolvedValueOnce(json({ error: { code: 'X', message: 'nope' } }, 401))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    await expect(apiRequest('/brands')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'UNAUTHORIZED',
    })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    const [logoutUrl, logoutInit] = fetchMock.mock.calls[1]
    expect(logoutUrl).toBe('/api/auth/logout')
    expect(logoutInit).toMatchObject({ method: 'POST', credentials: 'include' })
    expect(location.href).toBe('/login')
  })

  it('still goes to /login when the logout call fails', async () => {
    const location = stubLocation()
    fetchMock
      .mockResolvedValueOnce(json({}, 401))
      .mockRejectedValueOnce(new TypeError('network down'))

    await expect(apiRequest('/brands')).rejects.toBeInstanceOf(ApiError)
    expect(location.href).toBe('/login')
  })

  it('with redirectOn401: false surfaces the backend error and does not log out', async () => {
    const location = stubLocation()
    fetchMock.mockResolvedValueOnce(
      json(
        { error: { code: 'INVALID_CREDENTIALS', message: 'Bad login', request_id: 'r1' } },
        401,
      ),
    )

    await expect(
      apiRequest('/auth/login', { method: 'POST', redirectOn401: false }),
    ).rejects.toMatchObject({ code: 'INVALID_CREDENTIALS', message: 'Bad login', requestId: 'r1' })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(location.href).toBe('http://localhost/dashboard')
  })

  it('parses the backend error shape for non-401 failures', async () => {
    fetchMock.mockResolvedValueOnce(
      json({ error: { code: 'FORBIDDEN', message: 'No access', request_id: 'r2' } }, 403),
    )

    await expect(apiRequest('/admin')).rejects.toMatchObject({
      code: 'FORBIDDEN',
      message: 'No access',
      requestId: 'r2',
    })
  })

  it('logs out disabled accounts and redirects with the disabled flag', async () => {
    const location = stubLocation()
    fetchMock
      .mockResolvedValueOnce(json({ error: { code: 'ACCOUNT_DISABLED', message: 'Disabled' } }, 403))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(apiRequest('/admin/users')).rejects.toMatchObject({ code: 'ACCOUNT_DISABLED', status: 403 })
    expect(fetchMock.mock.calls[1]).toEqual(['/api/auth/logout', { method: 'POST', credentials: 'include' }])
    expect(location.href).toBe('/login?disabled=1')
  })

  it('redirects disabled accounts even when logout fails', async () => {
    const location = stubLocation()
    fetchMock
      .mockResolvedValueOnce(json({ error: { code: 'ACCOUNT_DISABLED', message: 'Disabled' } }, 403))
      .mockRejectedValueOnce(new TypeError('offline'))
    await expect(apiRequest('/brands')).rejects.toMatchObject({ code: 'ACCOUNT_DISABLED' })
    expect(location.href).toBe('/login?disabled=1')
  })

  it('surfaces ACCOUNT_DISABLED on login without redirecting or logging out', async () => {
    const location = stubLocation()
    fetchMock.mockResolvedValueOnce(json({ error: { code: 'ACCOUNT_DISABLED', message: 'Disabled' } }, 403))
    await expect(apiRequest('/auth/login', { redirectOn401: false, method: 'POST' })).rejects.toMatchObject({ code: 'ACCOUNT_DISABLED' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(location.href).toBe('http://localhost/dashboard')
  })

  it('returns null for 204 responses', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(apiRequest('/auth/logout', { method: 'POST' })).resolves.toBeNull()
  })
})

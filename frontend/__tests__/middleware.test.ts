// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { SignJWT } from 'jose'
import { NextRequest } from 'next/server'
import { middleware } from '@/middleware'

const SECRET = 'dev-secret-dev-secret-dev-secret-00'
const key = new TextEncoder().encode(SECRET)

async function sign(
  opts: { secret?: Uint8Array; exp?: string | number; iss?: string; aud?: string } = {},
) {
  return new SignJWT({ email: 'a@b.co' })
    .setProtectedHeader({ alg: 'HS256' })
    .setSubject('user-1')
    .setIssuedAt()
    .setIssuer(opts.iss ?? 'trendy-api')
    .setAudience(opts.aud ?? 'trendy')
    .setExpirationTime(opts.exp ?? '1h')
    .sign(opts.secret ?? key)
}

function request(path: string, token?: string) {
  const headers = token ? { cookie: `trendy_session=${token}` } : undefined
  return new NextRequest(`http://localhost:3000${path}`, { headers })
}

function redirectTarget(res: Response) {
  if (res.status < 300 || res.status >= 400) return null
  return new URL(res.headers.get('location') as string).pathname
}

beforeAll(() => {
  vi.stubEnv('AUTH_JWT_SECRET', SECRET)
})

describe('middleware', () => {
  describe('valid session cookie', () => {
    it('lets a logged-in user reach protected pages', async () => {
      const res = await middleware(request('/dashboard', await sign()))
      expect(redirectTarget(res)).toBeNull()
      expect(res.headers.get('x-middleware-next')).toBe('1')
    })

    it.each(['/login', '/signup'])('redirects %s to /dashboard', async (path) => {
      const res = await middleware(request(path, await sign()))
      expect(redirectTarget(res)).toBe('/dashboard')
    })

    it.each(['/forgot-password', '/verify-code', '/reset-password', '/reset-success'])(
      'does not redirect %s',
      async (path) => {
        const res = await middleware(request(path, await sign()))
        expect(redirectTarget(res)).toBeNull()
      },
    )
  })

  describe('missing cookie', () => {
    it('redirects protected pages to /login', async () => {
      for (const path of ['/dashboard', '/abc/generate', '/admin', '/account']) {
        const res = await middleware(request(path))
        expect(redirectTarget(res)).toBe('/login')
      }
    })

    it.each([
      '/',
      '/login',
      '/signup',
      '/forgot-password',
      '/verify-code',
      '/reset-password',
      '/reset-success',
      '/auth/confirm',
    ])('allows public path %s', async (path) => {
      const res = await middleware(request(path))
      expect(redirectTarget(res)).toBeNull()
    })
  })

  describe('invalid session cookie counts as logged out', () => {
    const cases: Array<[string, () => Promise<string>]> = [
      ['garbage', async () => 'not-a-jwt'],
      ['expired', () => sign({ exp: Math.floor(Date.now() / 1000) - 60 })],
      ['wrong secret', () => sign({ secret: new TextEncoder().encode('x'.repeat(40)) })],
      ['wrong issuer', () => sign({ iss: 'someone-else' })],
      ['wrong audience', () => sign({ aud: 'other' })],
    ]

    it.each(cases)('%s token redirects a protected page to /login', async (_name, make) => {
      const res = await middleware(request('/dashboard', await make()))
      expect(redirectTarget(res)).toBe('/login')
    })

    it.each(cases)('%s token can still open /login', async (_name, make) => {
      const res = await middleware(request('/login', await make()))
      expect(redirectTarget(res)).toBeNull()
    })
  })

  it('treats every request as logged out when AUTH_JWT_SECRET is not set', async () => {
    const token = await sign()
    vi.stubEnv('AUTH_JWT_SECRET', '')
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const res = await middleware(request('/dashboard', token))
      expect(redirectTarget(res)).toBe('/login')
    } finally {
      errorSpy.mockRestore()
      vi.stubEnv('AUTH_JWT_SECRET', SECRET)
    }
  })
})

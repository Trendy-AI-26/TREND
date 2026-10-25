import { jwtVerify } from 'jose'

/**
 * Edge-safe session helpers (no `next/headers` import) so they can be shared by
 * middleware and server components.
 *
 * The backend owns the session: it sets an httpOnly `trendy_session` cookie
 * holding an HS256 JWT signed with AUTH_JWT_SECRET. The frontend only verifies it.
 */
export const SESSION_COOKIE = 'trendy_session'
export const SESSION_ISSUER = 'trendy-api'
export const SESSION_AUDIENCE = 'trendy'

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  is_admin: boolean
  email_verified: boolean
}

export interface SessionClaims {
  userId: string
  email: string | null
}

/**
 * Verifies a session JWT. Returns the claims, or null when the token is
 * missing, malformed, expired, signed with another key, or has a wrong
 * issuer/audience. Never throws.
 */
export async function verifySessionToken(
  token: string | undefined | null,
): Promise<SessionClaims | null> {
  if (!token) return null

  const secret = process.env.AUTH_JWT_SECRET
  if (!secret) {
    console.error('AUTH_JWT_SECRET is not configured; treating request as logged out')
    return null
  }

  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret), {
      algorithms: ['HS256'],
      issuer: SESSION_ISSUER,
      audience: SESSION_AUDIENCE,
    })
    if (typeof payload.sub !== 'string' || !payload.sub) return null
    return {
      userId: payload.sub,
      email: typeof payload.email === 'string' ? payload.email : null,
    }
  } catch {
    return null
  }
}

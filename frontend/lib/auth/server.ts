import { cookies } from 'next/headers'
import {
  SESSION_COOKIE,
  verifySessionToken,
  type AuthUser,
  type SessionClaims,
} from './session'

export type { AuthUser } from './session'

export interface ServerSession extends SessionClaims {
  /** Raw JWT; send to the backend as `Authorization: Bearer <token>`. */
  token: string
}

/** Server-reachable backend base URL (the browser uses the `/api` rewrite). */
export function getBackendUrl(): string {
  return (process.env.NEXT_SERVER_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
}

/**
 * Reads the session cookie in a server component / route handler and verifies it.
 * Returns null when logged out (no cookie, invalid or expired token).
 */
export async function getServerSession(): Promise<ServerSession | null> {
  const token = cookies().get(SESSION_COOKIE)?.value
  const claims = await verifySessionToken(token)
  if (!token || !claims) return null
  return { ...claims, token }
}

/**
 * Fetches the full user (`is_admin`, `full_name`, ...) from the backend
 * `GET /auth/session`. Returns null when logged out or the backend rejects the token.
 */
export async function getSessionUser(
  session?: ServerSession | null,
): Promise<AuthUser | null> {
  const current = session ?? (await getServerSession())
  if (!current) return null

  const response = await fetch(`${getBackendUrl()}/auth/session`, {
    headers: { Authorization: `Bearer ${current.token}` },
    cache: 'no-store',
  })
  if (!response.ok) return null

  const payload = (await response.json()) as { user?: AuthUser }
  return payload.user ?? null
}

import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE, verifySessionToken } from '@/lib/auth/session'

export async function middleware(request: NextRequest) {
  // The backend owns the session cookie; an invalid/expired/missing token
  // counts as logged out.
  const user = await verifySessionToken(request.cookies.get(SESSION_COOKIE)?.value)

  const { pathname } = request.nextUrl

  // Auth pages: redirect authenticated users to /dashboard
  if (user && (pathname === '/login' || pathname === '/signup')) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // Protected routes: redirect unauthenticated users to /login
  const isPublicAuthFlow = [
    '/login',
    '/signup',
    '/forgot-password',
    '/verify-code',
    '/reset-password',
    '/reset-success',
  ].includes(pathname)
  if (!user && !isPublicAuthFlow && pathname !== '/' && !pathname.startsWith('/auth/')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  // `/api/*` is excluded: those requests are proxied to the backend (which
  // enforces auth itself) and must stay reachable while logged out, e.g.
  // POST /api/auth/login.
  matcher: [
    '/((?!api/|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}

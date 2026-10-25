import { type NextRequest, NextResponse } from 'next/server'

// The old e-mail-link confirmation flow no longer exists (users now enter a
// 6-digit code on /verify-code). Keep the URL alive for stale emails and just
// send people to the login page.
export async function GET(request: NextRequest) {
  const redirectTo = request.nextUrl.clone()
  redirectTo.pathname = '/login'
  redirectTo.search = ''
  return NextResponse.redirect(redirectTo)
}

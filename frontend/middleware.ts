import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => {
            request.cookies.set(name, value)
          })
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) => {
            supabaseResponse.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  // IMPORTANT: Use getUser() not getSession() for server-side validation
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const { pathname } = request.nextUrl

  // Auth pages: redirect authenticated users to /brands
  if (user && (pathname === '/login' || pathname === '/signup')) {
    const url = request.nextUrl.clone()
    url.pathname = '/brands'
    const redirectResponse = NextResponse.redirect(url)
    supabaseResponse.headers.getSetCookie().forEach((cookie) => {
      redirectResponse.headers.append('set-cookie', cookie)
    })
    return redirectResponse
  }

  // Password recovery pages must remain reachable before a recovery session exists.
  if (
    !user &&
    pathname !== '/login' &&
    pathname !== '/signup' &&
    pathname !== '/forgot-password' &&
    pathname !== '/reset-password' &&
    pathname !== '/' &&
    !pathname.startsWith('/auth/')
  ) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    const redirectResponse = NextResponse.redirect(url)
    supabaseResponse.headers.getSetCookie().forEach((cookie) => {
      redirectResponse.headers.append('set-cookie', cookie)
    })
    return redirectResponse
  }

  return supabaseResponse
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}

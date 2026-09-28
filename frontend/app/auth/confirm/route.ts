import { type NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const token_hash = searchParams.get('token_hash')
  const type = searchParams.get('type') as
    | 'signup'
    | 'invite'
    | 'magiclink'
    | 'recovery'
    | 'email_change'
    | 'email'
    | null

  const redirectTo = request.nextUrl.clone()
  const next = searchParams.get('next')

  if (token_hash && type) {
    const supabase = await createClient()
    const { error } = await supabase.auth.verifyOtp({ type, token_hash })

    if (!error) {
      redirectTo.pathname = type === 'recovery' && next?.startsWith('/') ? next : '/brands'
      redirectTo.searchParams.delete('token_hash')
      redirectTo.searchParams.delete('type')
      redirectTo.searchParams.delete('next')
      return NextResponse.redirect(redirectTo)
    }
  }

  // If verification fails or params missing, redirect to login
  redirectTo.pathname = '/login'
  redirectTo.searchParams.delete('token_hash')
  redirectTo.searchParams.delete('type')
  redirectTo.searchParams.delete('next')
  return NextResponse.redirect(redirectTo)
}

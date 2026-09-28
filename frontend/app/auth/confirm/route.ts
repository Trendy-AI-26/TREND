import { type NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const tokenHash = searchParams.get('token_hash')
  const type = searchParams.get('type')

  if (type !== 'recovery' || !tokenHash) {
    return NextResponse.redirect(new URL('/forgot-password?error=invalid-link', request.url))
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.verifyOtp({ type: 'recovery', token_hash: tokenHash })

  if (error) {
    return NextResponse.redirect(new URL('/forgot-password?error=expired-link', request.url))
  }

  return NextResponse.redirect(new URL('/reset-password', request.url))
}

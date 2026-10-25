import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const BACKEND_URL = process.env.NEXT_SERVER_API_URL ?? 'http://127.0.0.1:8000'

export async function POST(
  request: NextRequest,
  { params }: { params: { brandId: string } },
) {
  const body = await request.text()

  const headers: Record<string, string> = {
    'Content-Type': request.headers.get('content-type') ?? 'application/json',
  }
  const auth = request.headers.get('authorization')
  if (auth) headers['Authorization'] = auth
  const cookie = request.headers.get('cookie')
  if (cookie) headers['Cookie'] = cookie

  let upstream: Response
  try {
    upstream = await fetch(`${BACKEND_URL}/brands/${params.brandId}/preview-brief`, {
      method: 'POST',
      headers,
      body,
      signal: AbortSignal.timeout(30_000),
    })
  } catch (err) {
    const isTimeout = err instanceof Error && err.name === 'TimeoutError'
    const status = isTimeout ? 504 : 502
    const code = isTimeout ? 'GATEWAY_TIMEOUT' : 'BACKEND_UNREACHABLE'
    const message = isTimeout
      ? 'The preview request timed out. Please try again.'
      : 'Could not reach backend service.'
    return NextResponse.json(
      { error: { code, message, request_id: null } },
      { status },
    )
  }

  const responseBody = await upstream.text()
  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: {
      'Content-Type':
        upstream.headers.get('content-type') ?? 'application/json',
    },
  })
}

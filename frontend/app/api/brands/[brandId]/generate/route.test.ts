// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'
import { POST } from './route'
afterEach(() => { vi.unstubAllGlobals() })
it('forwards authentication, idempotency key and exact body, preserving failure status', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('{"error":{"code":"GENERATION_IN_PROGRESS"}}',
    { status: 409, headers: { 'Content-Type': 'application/json' } }))
  vi.stubGlobal('fetch', fetcher)
  const request = new NextRequest('http://localhost/api/brands/brand/generate', {
    method: 'POST', body: '{"x":1}',
    headers: { Authorization: 'Bearer fake', 'Idempotency-Key': 'stable-request-key' },
  })
  const response = await POST(request, { params: { brandId: 'brand' } })
  expect(response.status).toBe(409)
  expect(fetcher.mock.calls[0][1]).toMatchObject({ body: '{"x":1}', headers: {
    Authorization: 'Bearer fake', 'Idempotency-Key': 'stable-request-key',
  } })
})

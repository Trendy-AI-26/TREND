// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'
import { POST } from './route'

afterEach(() => {
  vi.unstubAllGlobals()
})

it('forwards cookie, authorization, idempotency key and exact body, preserving failure status', async () => {
  const fetcher = vi.fn().mockResolvedValue(
    new Response('{"error":{"code":"GENERATION_IN_PROGRESS"}}', {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetcher)
  const request = new NextRequest('http://localhost/api/brands/brand/generate', {
    method: 'POST',
    body: '{"x":1}',
    headers: {
      Authorization: 'Bearer fake',
      Cookie: 'session=abc',
      'Idempotency-Key': 'stable-request-key',
    },
  })
  const response = await POST(request, { params: { brandId: 'brand' } })
  expect(response.status).toBe(409)
  expect(fetcher.mock.calls[0][1]).toMatchObject({
    body: '{"x":1}',
    headers: {
      Authorization: 'Bearer fake',
      Cookie: 'session=abc',
      'Idempotency-Key': 'stable-request-key',
    },
  })
})

it('does not invent an idempotency key when the client sent none', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 400 }))
  vi.stubGlobal('fetch', fetcher)
  const request = new NextRequest('http://localhost/api/brands/brand/generate', {
    method: 'POST',
    body: '{}',
  })
  await POST(request, { params: { brandId: 'brand' } })
  expect(fetcher.mock.calls[0][1].headers).not.toHaveProperty('Idempotency-Key')
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, searchLivestreams } from './api'

describe('searchLivestreams API client', () => {
  const globalFetch = globalThis.fetch

  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    globalThis.fetch = globalFetch
    vi.restoreAllMocks()
  })

  it('sends POST request with query and null cursor on initial search', async () => {
    const mockResponse = {
      query: 'news',
      verified_at: '2026-07-22T10:00:00Z',
      results: [],
      has_more: true,
      next_cursor: 'opaque_cursor_1',
    }

    vi.mocked(globalThis.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const result = await searchLivestreams('news')

    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'news', cursor: null }),
    })
    expect(result).toEqual(mockResponse)
  })

  it('sends POST request with query and opaque cursor token on continuation search', async () => {
    const mockResponse = {
      query: 'news',
      verified_at: '2026-07-22T10:01:00Z',
      results: [],
      has_more: false,
      next_cursor: null,
    }

    vi.mocked(globalThis.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const result = await searchLivestreams('news', 'opaque_cursor_1')

    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'news', cursor: 'opaque_cursor_1' }),
    })
    expect(result).toEqual(mockResponse)
  })

  it('throws ApiError on non-200 HTTP response', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Public discovery service is unavailable' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await expect(searchLivestreams('news')).rejects.toThrow(ApiError)
  })
})

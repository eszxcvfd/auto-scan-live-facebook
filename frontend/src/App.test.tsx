import { cleanup, render, screen, fireEvent } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import * as api from './lib/api'
import type { SearchResponse } from './types'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
describe('App result handoff', () => {
  it('renders Facebook external link with expected destination, separate context, safe rel, and accessible name', async () => {
    vi.spyOn(api, 'searchLivestreams').mockResolvedValueOnce({
      query: 'championship',
      verified_at: '2026-07-21T12:00:00Z',
      results: [
        {
          id: 'live-101',
          title: 'Official Gaming Championship',
          source_name: 'Esports Channel',
          url: 'https://www.facebook.com/watch/?v=1000101',
          thumbnail_url: 'https://www.facebook.com/images/thumb101.jpg',
          started_at: '2026-07-21T11:30:00Z',
          verified_at: '2026-07-21T12:00:00Z',
          is_live: true,
          is_replay: false,
        },
      ],
    })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    const submitButton = screen.getByRole('button', { name: /search live/i })

    fireEvent.change(input, { target: { value: 'championship' } })
    fireEvent.click(submitButton)

    const link = await screen.findByRole('link', {
      name: /open official gaming championship on facebook/i,
    })

    expect(link.getAttribute('href')).toBe('https://www.facebook.com/watch/?v=1000101')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toContain('noreferrer')
    expect(link.getAttribute('aria-label')).toBe('Open Official Gaming Championship on Facebook')
    const heading = screen.getByRole('heading', { name: 'Official Gaming Championship' })
    expect(heading.getAttribute('title')).toBe('Official Gaming Championship')
  })
})
describe('App accessible operator workflow', () => {
  it('prevents duplicate search submissions while a search is loading', async () => {
    let resolvePromise: (value: SearchResponse) => void = () => {}
    const pendingPromise = new Promise<SearchResponse>((resolve) => {
      resolvePromise = resolve
    })

    const searchSpy = vi.spyOn(api, 'searchLivestreams').mockReturnValue(pendingPromise)

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    const submitButton = screen.getByRole('button', { name: /search live/i })
    const form = input.closest('form')!

    fireEvent.change(input, { target: { value: 'gaming' } })
    fireEvent.submit(form)

    expect(searchSpy).toHaveBeenCalledTimes(1)

    // Attempt second submission while loading (e.g. via form submit or button click)
    fireEvent.submit(form)
    fireEvent.click(submitButton)

    expect(searchSpy).toHaveBeenCalledTimes(1)

    // Resolve initial request
    resolvePromise({
      query: 'gaming',
      verified_at: '2026-07-21T12:00:00Z',
      results: [],
    })

    await screen.findByRole('heading', { name: /nothing live for “gaming”/i })
  })

  it('ensures primary workflow interactive controls are focusable for keyboard navigation', async () => {
    vi.spyOn(api, 'searchLivestreams').mockResolvedValueOnce({
      query: 'gaming',
      verified_at: '2026-07-21T12:00:00Z',
      results: [
        {
          id: 'live-1',
          title: 'Gaming Stream',
          source_name: 'Gamer Channel',
          url: 'https://www.facebook.com/watch/?v=1',
          thumbnail_url: '',
          started_at: '2026-07-21T11:30:00Z',
          verified_at: '2026-07-21T12:00:00Z',
          is_live: true,
          is_replay: false,
        },
      ],
    })

    render(<App />)

    const brandLink = screen.getByRole('link', { name: /livescout home/i })
    const searchInput = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    const submitButton = screen.getByRole('button', { name: /search live/i })
    const suggestionButton = screen.getByRole('button', { name: 'gaming' })

    brandLink.focus()
    expect(document.activeElement).toBe(brandLink)

    searchInput.focus()
    expect(document.activeElement).toBe(searchInput)

    submitButton.focus()
    expect(document.activeElement).toBe(submitButton)

    suggestionButton.focus()
    expect(document.activeElement).toBe(suggestionButton)

    fireEvent.click(suggestionButton)

    const resultLink = await screen.findByRole('link', { name: /open gaming stream on facebook/i })
    resultLink.focus()
    expect(document.activeElement).toBe(resultLink)
  })

  it('associates validation error with input using aria-invalid and aria-describedby', async () => {
    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    const submitButton = screen.getByRole('button', { name: /search live/i })

    expect(input.getAttribute('aria-invalid')).toBe('false')
    expect(input.getAttribute('aria-describedby')).toBeNull()

    // Submit empty search
    fireEvent.click(submitButton)

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toMatch(/invalid search query/i)

    const errorDesc = screen.getByText(/enter a keyword to find public livestreams/i)
    expect(errorDesc.id).toBe('validation-error-desc')

    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(input.getAttribute('aria-describedby')).toBe('validation-error-desc')
  })

  it('renders discovery error state with a working keyboard-accessible retry action', async () => {
    const searchSpy = vi
      .spyOn(api, 'searchLivestreams')
      .mockRejectedValueOnce(new api.ApiError('Public discovery service is offline.', 503))
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-21T12:00:00Z',
        results: [],
      })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    const submitButton = screen.getByRole('button', { name: /search live/i })

    fireEvent.change(input, { target: { value: 'news' } })
    fireEvent.click(submitButton)

    const retryButton = await screen.findByRole('button', { name: /retry search for news/i })
    expect(retryButton).toBeDefined()
    expect(searchSpy).toHaveBeenCalledTimes(1)

    fireEvent.click(retryButton)

    await screen.findByRole('heading', { name: /nothing live for “news”/i })
    expect(searchSpy).toHaveBeenCalledTimes(2)
  })
})
describe('App pagination and continuation workflow', () => {
  function createMockResult(id: string, title = `Stream ${id}`) {
    return {
      id,
      title,
      source_name: `Channel ${id}`,
      url: `https://www.facebook.com/watch/?v=${id}`,
      thumbnail_url: null,
      started_at: '2026-07-22T10:00:00Z',
      verified_at: '2026-07-22T10:00:00Z',
      is_live: true,
      is_replay: false,
    }
  }

  it('renders Show More button when initial batch has more results', async () => {
    vi.spyOn(api, 'searchLivestreams').mockResolvedValueOnce({
      query: 'news',
      verified_at: '2026-07-22T10:00:00Z',
      results: Array.from({ length: 10 }, (_, i) => createMockResult(`news-${i + 1}`)),
      has_more: true,
      next_cursor: 'token-page-2',
    })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    fireEvent.change(input, { target: { value: 'news' } })
    fireEvent.click(screen.getByRole('button', { name: /search live/i }))

    await screen.findByRole('heading', { name: /10 live broadcasts/i })

    const showMoreBtn = screen.getByRole('button', { name: /show more live results for news/i })
    expect(showMoreBtn).toBeDefined()
  })

  it('appends continuation batch to existing results when Show More is clicked', async () => {
    const searchSpy = vi
      .spyOn(api, 'searchLivestreams')
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:00:00Z',
        results: Array.from({ length: 10 }, (_, i) => createMockResult(`news-${i + 1}`)),
        has_more: true,
        next_cursor: 'token-page-2',
      })
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:05:00Z',
        results: Array.from({ length: 5 }, (_, i) => createMockResult(`news-${i + 11}`)),
        has_more: false,
        next_cursor: null,
      })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    fireEvent.change(input, { target: { value: 'news' } })
    fireEvent.click(screen.getByRole('button', { name: /search live/i }))

    const showMoreBtn = await screen.findByRole('button', { name: /show more live results for news/i })
    fireEvent.click(showMoreBtn)

    expect(searchSpy).toHaveBeenLastCalledWith('news', 'token-page-2')

    await screen.findByRole('heading', { name: /15 live broadcasts/i })
    expect(screen.getByText('Stream news-1')).toBeDefined()
    expect(screen.getByText('Stream news-15')).toBeDefined()
  })

  it('prevents concurrent Show More requests while continuation loading is pending', async () => {
    let resolveContinuation: (value: SearchResponse) => void = () => {}
    const pendingContinuation = new Promise<SearchResponse>((resolve) => {
      resolveContinuation = resolve
    })

    const searchSpy = vi
      .spyOn(api, 'searchLivestreams')
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:00:00Z',
        results: Array.from({ length: 10 }, (_, i) => createMockResult(`news-${i + 1}`)),
        has_more: true,
        next_cursor: 'token-page-2',
      })
      .mockReturnValueOnce(pendingContinuation)

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    fireEvent.change(input, { target: { value: 'news' } })
    fireEvent.click(screen.getByRole('button', { name: /search live/i }))

    const showMoreBtn = await screen.findByRole('button', { name: /show more live results for news/i })
    fireEvent.click(showMoreBtn)

    expect(searchSpy).toHaveBeenCalledTimes(2)

    // Click again while continuation is pending
    fireEvent.click(showMoreBtn)
    expect(searchSpy).toHaveBeenCalledTimes(2)

    resolveContinuation({
      query: 'news',
      verified_at: '2026-07-22T10:05:00Z',
      results: Array.from({ length: 3 }, (_, i) => createMockResult(`news-${i + 11}`)),
      has_more: false,
      next_cursor: null,
    })

    await screen.findByRole('heading', { name: /13 live broadcasts/i })
  })

  it('deduplicates duplicate result IDs returned in continuation batch', async () => {
    vi.spyOn(api, 'searchLivestreams')
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:00:00Z',
        results: [createMockResult('news-1'), createMockResult('news-2')],
        has_more: true,
        next_cursor: 'token-page-2',
      })
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:05:00Z',
        results: [createMockResult('news-2'), createMockResult('news-3')],
        has_more: false,
        next_cursor: null,
      })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    fireEvent.change(input, { target: { value: 'news' } })
    fireEvent.click(screen.getByRole('button', { name: /search live/i }))

    const showMoreBtn = await screen.findByRole('button', { name: /show more live results for news/i })
    fireEvent.click(showMoreBtn)

    await screen.findByRole('heading', { name: /3 live broadcasts/i })
    const news2Elements = screen.getAllByText('Stream news-2')
    expect(news2Elements).toHaveLength(1)
  })

  it('renders exhaustion indicator when discovery surface is exhausted (has_more is false)', async () => {
    vi.spyOn(api, 'searchLivestreams')
      .mockResolvedValueOnce({
        query: 'niche topic',
        verified_at: '2026-07-22T10:00:00Z',
        results: [createMockResult('niche-1')],
        has_more: false,
        next_cursor: null,
      })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    fireEvent.change(input, { target: { value: 'niche topic' } })
    fireEvent.click(screen.getByRole('button', { name: /search live/i }))

    await screen.findByRole('heading', { name: /1 live broadcast/i })

    expect(screen.queryByRole('button', { name: /show more/i })).toBeNull()
    expect(screen.getByText(/no more live results found for “niche topic”/i)).toBeDefined()
  })

  it('preserves existing results and shows error notice when continuation request fails', async () => {
    const searchSpy = vi
      .spyOn(api, 'searchLivestreams')
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:00:00Z',
        results: Array.from({ length: 10 }, (_, i) => createMockResult(`news-${i + 1}`)),
        has_more: true,
        next_cursor: 'token-page-2',
      })
      .mockRejectedValueOnce(new api.ApiError('Public discovery service is offline.', 503))
      .mockResolvedValueOnce({
        query: 'news',
        verified_at: '2026-07-22T10:05:00Z',
        results: Array.from({ length: 2 }, (_, i) => createMockResult(`news-${i + 11}`)),
        has_more: false,
        next_cursor: null,
      })

    render(<App />)

    const input = screen.getByRole('textbox', { name: /search public facebook livestreams/i })
    fireEvent.change(input, { target: { value: 'news' } })
    fireEvent.click(screen.getByRole('button', { name: /search live/i }))

    const showMoreBtn = await screen.findByRole('button', { name: /show more live results for news/i })
    fireEvent.click(showMoreBtn)

    // Existing 10 results remain visible
    await screen.findByText('Public discovery service is offline.')
    expect(screen.getByRole('heading', { name: /10 live broadcasts/i })).toBeDefined()
    expect(screen.getByText('Stream news-1')).toBeDefined()

    // Retry loading more
    const retryAppendBtn = screen.getByRole('button', { name: /retry loading more/i })
    fireEvent.click(retryAppendBtn)

    await screen.findByRole('heading', { name: /12 live broadcasts/i })
    expect(searchSpy).toHaveBeenCalledTimes(3)
  })
})

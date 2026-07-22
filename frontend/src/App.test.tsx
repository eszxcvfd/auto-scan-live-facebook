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

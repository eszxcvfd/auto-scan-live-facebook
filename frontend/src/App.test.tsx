import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import App from './App'
import * as api from './lib/api'

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

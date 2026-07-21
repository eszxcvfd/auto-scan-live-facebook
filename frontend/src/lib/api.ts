import type { SearchResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function searchLivestreams(query: string): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? 'The search could not be completed.')
  }

  return response.json() as Promise<SearchResponse>
}

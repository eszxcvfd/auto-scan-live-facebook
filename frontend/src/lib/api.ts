import type { SearchResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function searchLivestreams(
  query: string,
  cursor?: string | null
): Promise<SearchResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, cursor: cursor ?? null }),
    })
  } catch {
    throw new ApiError('Public discovery service is offline or unreachable. Check your server connection.', 503)
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    const message = body?.detail ?? 'The search could not be completed.'
    throw new ApiError(message, response.status)
  }

  return response.json() as Promise<SearchResponse>
}

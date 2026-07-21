export type LivestreamResult = {
  id: string
  title: string
  source_name: string
  url: string
  thumbnail_url: string | null
  started_at: string | null
  verified_at: string
  is_live: boolean
  is_replay: boolean
}

export type SearchResponse = {
  query: string
  verified_at: string
  results: LivestreamResult[]
}

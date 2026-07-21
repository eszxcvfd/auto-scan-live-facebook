import { useState, type FormEvent } from 'react'
import {
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from 'lucide-react'

import { Badge } from './components/ui/badge'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { searchLivestreams, ApiError } from './lib/api'
import type { LivestreamResult } from './types'
import './App.css'

type SearchState = 'idle' | 'loading' | 'success' | 'validation_error' | 'discovery_error'
const exampleQueries = ['gaming', 'music', 'news', 'football']

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

function ResultRow({ result }: { result: LivestreamResult }) {
  const hasThumbnail = Boolean(result.thumbnail_url && result.thumbnail_url.trim())
  return (
    <article className="result-row">
      <div
        className={`result-art ${hasThumbnail ? 'has-image' : ''}`}
        style={hasThumbnail ? { backgroundImage: `url(${result.thumbnail_url})` } : undefined}
        aria-hidden="true"
      >
        {!hasThumbnail && <Radio size={24} strokeWidth={1.5} />}
        <span className="result-art-live"><span /> LIVE</span>
      </div>
      <div className="result-copy">
        <div className="result-heading">
          <h3>{result.title}</h3>
          <Badge>Verified live</Badge>
        </div>
        <p className="result-source">{result.source_name}</p>
        <div className="result-meta">
          <span><ShieldCheck size={14} /> Checked at {formatTime(result.verified_at)}</span>
          <span><Clock3 size={14} /> Public discovery</span>
        </div>
      </div>
      <a
        className="result-link"
        href={result.url}
        target="_blank"
        rel="noreferrer"
        aria-label={`Open ${result.title} on Facebook`}
      >
        <span>Open on Facebook</span>
        <ExternalLink size={16} />
      </a>
    </article>
  )
}

function LoadingResults() {
  return (
    <div className="result-list" aria-label="Loading live results" aria-busy="true">
      {[1, 2, 3].map((item) => (
        <div className="result-row skeleton-row" key={item}>
          <div className="skeleton skeleton-art" />
          <div className="skeleton-copy">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line short" />
          </div>
        </div>
      ))}
    </div>
  )
}

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<LivestreamResult[]>([])
  const [verifiedAt, setVerifiedAt] = useState<string | null>(null)
  const [state, setState] = useState<SearchState>('idle')
  const [error, setError] = useState('')

  async function handleSearch(value = query) {
    const nextQuery = value.trim()
    setResults([])
    setVerifiedAt(null)

    if (!nextQuery) {
      setError('Enter a keyword to find public livestreams.')
      setState('validation_error')
      return
    }

    setQuery(nextQuery)
    setState('loading')
    setError('')

    try {
      const response = await searchLivestreams(nextQuery)
      setResults(response.results)
      setVerifiedAt(response.verified_at)
      setState('success')
    } catch (searchError) {
      setResults([])
      setVerifiedAt(null)
      const message = searchError instanceof Error ? searchError.message : 'The search could not be completed.'
      setError(message)
      if (searchError instanceof ApiError && searchError.status === 422) {
        setState('validation_error')
      } else {
        setState('discovery_error')
      }
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void handleSearch()
  }
  return (
    <main className="app-shell">
      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand" href="/" aria-label="LiveScout home">
          <span className="brand-mark"><Radio size={17} /></span>
          <span>LiveScout</span>
        </a>
        <div className="topbar-status"><span /> Public discovery</div>
      </nav>

      <section className="hero-section">
        <div className="eyebrow"><span className="eyebrow-dot" /> Facebook live discovery</div>
        <h1>Find what&apos;s live<br /><em>right now.</em></h1>
        <p className="hero-copy">
          Search public Facebook broadcasts by keyword. Every result is checked at search time, so replays stay out of your way.
        </p>

        <form className="search-form" onSubmit={onSubmit}>
          <div className="search-field">
            <Search size={20} aria-hidden="true" />
            <Input
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                if (state === 'validation_error') {
                  setError('')
                  setState('idle')
                }
              }}
              placeholder="What do you want to watch?"
              aria-label="Search public Facebook livestreams"
              autoComplete="off"
            />
            <kbd>⌘ K</kbd>
          </div>
          <Button type="submit" disabled={state === 'loading'}>
            {state === 'loading' ? <RefreshCw className="spin" size={17} /> : <Search size={17} />}
            {state === 'loading' ? 'Searching' : 'Search live'}
          </Button>
        </form>

        <div className="query-suggestions" aria-label="Example searches">
          <span>Try</span>
          {exampleQueries.map((example) => (
            <button type="button" key={example} onClick={() => void handleSearch(example)}>{example}</button>
          ))}
        </div>
      </section>

      <section className="results-section" aria-live="polite">
        <div className="results-header">
          <div>
            <p className="section-kicker">Search results</p>
            <h2>{state === 'success' ? `${results.length} live ${results.length === 1 ? 'broadcast' : 'broadcasts'}` : 'Ready when you are'}</h2>
          </div>
          {verifiedAt && state === 'success' && (
            <div className="verification-note"><CheckCircle2 size={15} /> Checked at {formatTime(verifiedAt)}</div>
          )}
        </div>

        {state === 'loading' && <LoadingResults />}

        {state === 'validation_error' && (
          <div className="state-panel validation-panel" role="alert">
            <div className="state-icon validation-icon"><TriangleAlert size={22} /></div>
            <div>
              <h3>Invalid search query</h3>
              <p>{error}</p>
            </div>
          </div>
        )}

        {state === 'discovery_error' && (
          <div className="state-panel error-panel" role="alert">
            <div className="state-icon"><TriangleAlert size={22} /></div>
            <div>
              <h3>Public discovery unavailable</h3>
              <p>{error}</p>
            </div>
            <Button
              variant="secondary"
              size="small"
              onClick={() => void handleSearch(query)}
              aria-label={`Retry search for ${query}`}
            >
              <RefreshCw size={15} /> Retry search
            </Button>
          </div>
        )}

        {state === 'success' && results.length === 0 && (
          <div className="state-panel empty-panel">
            <div className="state-icon"><Sparkles size={22} /></div>
            <div>
              <h3>Nothing live for “{query}”</h3>
              <p>Try a broader keyword. We only show broadcasts verified as live right now.</p>
            </div>
          </div>
        )}

        {state === 'success' && results.length > 0 && (
          <div className="result-list">
            {results.map((result) => <ResultRow key={result.id} result={result} />)}
          </div>
        )}

        {state === 'idle' && (
          <div className="welcome-panel">
            <div className="welcome-orbit"><span className="orbit-dot one" /><span className="orbit-dot two" /><Radio size={29} /></div>
            <div>
              <h3>Live, not later</h3>
              <p>Enter a topic and we&apos;ll verify public results before they reach your list.</p>
            </div>
            <ArrowUpRight className="welcome-arrow" size={20} />
          </div>
        )}
      </section>

      <footer className="footer">
        <span><ShieldCheck size={14} /> Public pages only</span>
        <span>Coverage is best-effort</span>
        <span>Results open on Facebook <ExternalLink size={13} /></span>
      </footer>
    </main>
  )
}

export default App

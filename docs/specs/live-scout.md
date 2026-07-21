# LiveScout Specification

## Problem Statement

An operator needs to find Facebook livestreams that are active at the search moment. Ordinary video search can mix live broadcasts with recordings, replays, premieres, and ended videos, making it difficult to trust whether a result is actually live. The operator also does not want to manually inspect many Facebook pages or use an interface that implies complete coverage of Facebook.

## Solution

LiveScout is a local web application that lets a single operator enter a search query and discover publicly discoverable livestreams across Facebook's public discovery surfaces. It uses browser automation to find candidate broadcasts, performs live verification before returning a discovery result, excludes recordings and replays, and opens selected broadcasts on Facebook for playback.

The product provides best-effort discovery coverage. It does not claim to find every livestream on Facebook, access private content, or guarantee that a broadcast remains live after its verification time.

## User Stories

1. As an operator, I want to enter a keyword or phrase, so that I can search for relevant publicly discoverable livestreams.
2. As an operator, I want the search field to reject an empty or whitespace-only query, so that I receive a useful validation message instead of an unbounded Facebook scan.
3. As an operator, I want leading and trailing whitespace removed from my query, so that accidental spacing does not change the search.
4. As an operator, I want to submit a search with a button, so that the primary action is obvious.
5. As an operator, I want to submit a search from the keyboard, so that I can work quickly without leaving the search field.
6. As an operator, I want example queries available before my first search, so that I understand what kinds of topics I can search for.
7. As an operator, I want immediate loading feedback after submitting a query, so that I know the application is discovering and verifying broadcasts.
8. As an operator, I want the interface to prevent duplicate submissions while a search is running, so that one action does not create competing discovery sessions.
9. As an operator, I want every displayed result to be a verified live broadcast, so that the result list answers the question “what is live now?”
10. As an operator, I want recordings excluded, so that historical video does not appear as current discovery.
11. As an operator, I want replays excluded, so that rebroadcast content does not appear as an active live broadcast.
12. As an operator, I want premieres excluded, so that scheduled or prerecorded video is not presented as live.
13. As an operator, I want ended broadcasts excluded, so that stale results do not appear in the live list.
14. As an operator, I want candidates that cannot be verified to be excluded, so that uncertainty is not represented as a verified live state.
15. As an operator, I want each result to show when live verification occurred, so that I can judge the freshness of the result.
16. As an operator, I want each result to show a clear live indicator, so that I can scan the list quickly.
17. As an operator, I want each result to show its title, so that I can identify the broadcast before opening it.
18. As an operator, I want each result to show its source name when available, so that I can understand who or what published it.
19. As an operator, I want an optional thumbnail when Facebook exposes one, so that visual content helps me choose between results.
20. As an operator, I want repeated appearances of the same broadcast collapsed into one discovery result, so that the list remains readable.
21. As an operator, I want a result to expose its Facebook URL, so that I can inspect or watch the broadcast at the source.
22. As an operator, I want the Facebook destination to open in a separate browser context, so that my search results remain available.
23. As an operator, I want LiveScout to open playback on Facebook instead of copying or replaying the broadcast, so that Facebook remains the source of truth for viewing.
24. As an operator, I want a clear empty state when no verified live broadcast matches my query, so that I know the search completed successfully.
25. As an operator, I want the empty state to suggest using a broader query, so that I have a useful next action.
26. As an operator, I want a clear error state when public discovery is unavailable, so that CAPTCHA, rate limits, timeouts, or browser failures are not mistaken for zero results.
27. As an operator, I want to retry a failed search without retyping the query, so that transient discovery failures are easy to recover from.
28. As an operator, I want the original query and its verification timestamp retained after a successful search, so that I understand what the current result list represents.
29. As an operator, I want the interface to state that discovery coverage is best-effort, so that I do not mistake the result list for a complete Facebook inventory.
30. As an operator, I want the interface to state that only public pages are searched, so that the product's access boundary is clear.
31. As an operator, I want the application to avoid automatic login, so that it does not act on private account content without an explicit user action.
32. As an operator, I want searches to run locally, so that the initial product does not require a hosted account or multi-user service.
33. As an operator, I want the primary workflow centered on search and result scanning, so that unrelated dashboard metrics do not distract from discovery.
34. As an operator, I want a focused dark interface with restrained colors, so that the application remains comfortable during extended desktop use.
35. As an operator, I want coral reserved for live status, so that the meaning of the live indicator is consistent.
36. As an operator, I want blue used for search actions, links, and focus, so that interaction affordances are easy to recognize.
37. As an operator, I want keyboard focus to be visible, so that I can navigate the search workflow without a mouse.
38. As an operator, I want controls and links to have accessible names, so that assistive technology can describe the workflow.
39. As an operator, I want loading, empty, error, and success states to communicate meaning without relying on color alone, so that the workflow remains understandable in different accessibility contexts.
40. As an operator, I want decorative motion reduced or disabled when my system requests reduced motion, so that the interface does not create discomfort.
41. As an operator, I want the search workflow to remain usable on narrower screens, so that the local web app does not fail when the browser window is resized.
42. As an operator, I want a health status endpoint for the local service, so that the frontend and local setup can determine whether the backend is available.

## Implementation Decisions

- The product is a local web application for one desktop operator. Hosted multi-user accounts, shared search history, and remote deployment are not part of this spec.
- The backend uses Python and FastAPI. Browser discovery is performed with Playwright against public Facebook discovery pages.
- The frontend uses React and TypeScript. UI primitives follow shadcn/ui conventions and remain locally editable for visual customization.
- Browser automation must not automatically log in or access private Facebook content.
- A search requires a non-empty keyword or phrase. The query is normalized before discovery.
- The highest testing seam is the HTTP search contract:

  ```text
  POST /api/search
  Request:  { "query": string }
  Response: {
    "query": string,
    "verified_at": datetime,
    "results": [
      {
        "id": string,
        "title": string,
        "source_name": string,
        "url": string,
        "thumbnail_url": string | null,
        "started_at": datetime | null,
        "verified_at": datetime,
        "is_live": boolean,
        "is_replay": boolean
      }
    ]
  }
  ```

- The discovery boundary returns candidates, while the search service returns only candidates marked live, not marked as replay, and unique by stable identifier.
- A candidate must be opened and live-verified before it can become a discovery result. A result is valid only at its verification time.
- Discovery failures are represented separately from a successful search with zero results. Invalid queries return a client validation error; unavailable discovery returns a service-unavailable error.
- The result list contains metadata and a Facebook link. LiveScout does not copy, embed, download, record, or replay broadcasts.
- The frontend must implement idle, loading, success with results, success with no results, validation error, and discovery error states.
- The interface must expose verification time, public-only access, and best-effort coverage as explicit product language.
- The visual system is a restrained dark product UI with warm graphite surfaces, blue interaction accents, coral live indicators, readable system typography, and short state-driven motion.
- No persistent database or search-history schema is required for the initial feature.

## Testing Decisions

- Good tests verify observable behavior through the highest public interface available. They must describe what the operator or API consumer can observe and must not assert private functions, internal call order, CSS implementation details, or browser locator details.
- The primary seam is the HTTP `POST /api/search` contract with the external discovery boundary replaced by a test implementation. This keeps the test at the application boundary while avoiding live Facebook traffic, CAPTCHA, rate limits, and nondeterministic public content.
- API tests cover query normalization, blank-query rejection, filtering of non-live and replay results, duplicate removal, response shape, and discovery-unavailable errors.
- Browser discovery should have a small number of boundary tests only when stable fixtures are available. Do not make the core suite depend on live Facebook pages.
- Frontend behavior is validated against the API contract and through build/type/lint checks. Visual verification should cover idle, loading, empty, error, and populated result states, including keyboard focus and reduced-motion behavior.
- Existing repository prior art uses asynchronous HTTP tests against the ASGI application with a fake discovery boundary. New tests should extend that style rather than mocking internal service modules.

## Out of Scope

- Exhaustive inventory of every Facebook livestream.
- Private profiles, private groups, private events, or content requiring automatic login.
- Automatic Facebook account creation, login, cookie management, or credential storage.
- Downloading, recording, rebroadcasting, embedding, or in-app playback of livestreams.
- Search without a keyword or phrase.
- Hosted deployment, multi-user accounts, team workspaces, permissions, billing, or shared history.
- Persistent search history, favorites, notifications, scheduled searches, or alerts.
- Advanced filters such as country, language, category, viewer count, or time range in the initial feature.
- Analytics, engagement metrics, chat, comments, reactions, or moderation.
- Guaranteed bypass of CAPTCHA, rate limits, anti-bot systems, or Facebook UI changes.
- Support for non-Facebook platforms.

## Further Notes

The product's central promise is temporal: a discovery result means “verified live at this search moment,” not “guaranteed to remain live.” Discovery coverage is intentionally described as best-effort because public search indexing, page availability, browser automation, CAPTCHA, rate limits, and Facebook UI changes can all affect what is found.

The current implementation already provides an initial vertical slice of the search contract and local web interface. The next implementation work should harden browser discovery against real public-page variations, preserve the fail-closed live-verification rule, and add focused contract coverage before expanding the UI surface.

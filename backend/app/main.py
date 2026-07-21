from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .discovery import FacebookBrowserDiscovery
from .models import SearchRequest, SearchResponse
from .service import (
    DiscoveryPort,
    DiscoveryUnavailable,
    normalize_query,
    verified_live_results,
)


def create_app(discovery: DiscoveryPort | None = None) -> FastAPI:
    app = FastAPI(title="LiveScout API", version="0.1.0")
    app.state.discovery = discovery or FacebookBrowserDiscovery()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/search", response_model=SearchResponse)
    async def search(payload: SearchRequest, request: Request) -> SearchResponse:
        query = normalize_query(payload.query)
        if not query:
            raise HTTPException(
                status_code=422,
                detail="Search query must contain at least one non-whitespace character.",
            )

        try:
            discovered = await request.app.state.discovery.search(query)
        except DiscoveryUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        verified_at = datetime.now(timezone.utc)
        return SearchResponse(
            query=query,
            verified_at=verified_at,
            results=verified_live_results(discovered),
        )

    return app


app = create_app()

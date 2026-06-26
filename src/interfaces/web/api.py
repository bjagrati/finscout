"""FastAPI app for FinScout: web UI + streaming research endpoint."""
import sys
import json
from pathlib import Path

# Make 'core.*' imports work when uvicorn launches us
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.agent import research_stream


_SCREENSHOTS_DIR = Path(__file__).parent.parent.parent.parent / "screenshots"

app = FastAPI(
    title="FinScout",
    description="AI-powered stock research agent",
    version="1.0.0",
)


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "FinScout",
        "version": "1.0.0",
        "ui": "/ui",
        "docs": "/docs",
    }


@app.get("/research/{ticker}", tags=["research"])
def research_endpoint(ticker: str):
    """Stream research progress for a ticker via Server-Sent Events.
    
    Returns an event stream. Each event is JSON with a `type` field:
      progress      — text status update
      source_done   — finished extracting one source
      complete      — final ResearchBrief
      error         — fatal error
    """
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 8 or not ticker.isalpha():
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    
    def event_stream():
        try:
            for event in research_stream(ticker):
                # Pydantic models need explicit serialization
                if event["type"] == "complete":
                    payload = {
                        "type": "complete",
                        "brief": event["brief"].model_dump(),
                    }
                else:
                    payload = event
                # SSE format: 'data: <json>\n\n'
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception as e:
            # If anything escapes, emit a final error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
        },
    )


# Screenshots served from the screenshots/ folder
@app.get("/screenshots/{filename}", tags=["screenshots"])
def get_screenshot(filename: str):
    """Serve a screenshot file. Validates filename to prevent path traversal."""
    if "/" in filename or ".." in filename or not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    
    path = _SCREENSHOTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    
    return FileResponse(str(path), media_type="image/png")


# Static UI
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/ui", StaticFiles(directory=str(_STATIC_DIR), html=True), name="ui")
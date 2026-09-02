# app/main.py
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Import existing router matrices
from app.api.v1.endpoints.scanner import router as scanner_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whereabouts Visual Intelligence Platform",
    version="1.0.0"
)

# Protect Cross-Origin Resource Sharing boundaries for UI interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the Version 1 API Routing Matrices 
app.include_router(scanner_router, prefix="/api/v1/scanner")

# --- ENTERPRISE PRODUCTION FRONTEND ROUTING LAYER ---

@app.get("/map", response_class=HTMLResponse, tags=["Telemetry Dashboard"])
async def render_live_telemetry_dashboard(request: Request):
    """
    Serves the live tracking and mapping interface natively over HTTP.
    Bypasses tile provider anti-scraping policies by generating valid Referer headers.
    """
    template_path = Path("app/templates/map.html")
    
    if not template_path.exists():
        logger.error(f"Critical View Defect: UI template asset missing at: {template_path.resolve()}")
        return HTMLResponse(
            content="<h3>❌ Error 500: System Telemetry Dashboard Asset Missing on Server.</h3>", 
            status_code=500
        )
        
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"), status_code=200)

"""FastAPI Server & REST API for AI Blog Generator.

Endpoints:
    POST /api/generate   — Generate a new blog article
    GET  /api/health     — Health check & server status
    GET  /api/templates  — List available HTML templates
    GET  /api/blogs      — List previously generated blogs
    GET  /docs           — Interactive Swagger UI (auto-generated)
    GET  /redoc          — ReDoc API documentation (auto-generated)

Static Mounts:
    /output  — Serves generated blog output files
    /        — Serves the blog-dashboard frontend
"""

import os
import sys
import io
import time
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure UTF-8 stdout encoding for Windows console
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
import uvicorn

from blog_agent import (
    BlogAgentDeps,
    get_llm_model,
    run_3_iteration_blog_pipeline,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORT = int(os.getenv("PORT", "8000"))
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(WORKSPACE_DIR, "blog-dashboard")


def get_default_output_dir() -> str:
    """Return a writable output directory, falling back to /tmp on Vercel or read-only filesystems."""
    if os.getenv("VERCEL") or not os.access(WORKSPACE_DIR, os.W_OK):
        tmp_dir = os.path.join(tempfile.gettempdir(), "hireko_output")
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir
    default_dir = os.path.join(WORKSPACE_DIR, "output")
    os.makedirs(default_dir, exist_ok=True)
    return default_dir


DEFAULT_OUTPUT_DIR = get_default_output_dir()

TEMPLATE_CHOICES = [
    "Hireko Editorial",
    "Hireko Vercel Editorial",
]

SERVER_START_TIME = datetime.now(timezone.utc)
LATEST_GENERATED_HTML: Dict[str, str] = {}

# ---------------------------------------------------------------------------
# Pydantic Request / Response Models
# ---------------------------------------------------------------------------


class BlogGenerateRequest(BaseModel):
    """Request body for blog generation."""

    topic: str = Field(
        default="AI Agents & Modern Software Architecture",
        description="The blog topic to write about",
        examples=["AI Agents & Modern Software Architecture"],
    )
    audience_segment: str = Field(
        default="Software Engineers & Tech Leaders",
        description="Target audience for the article",
        examples=["Software Engineers & Tech Leaders"],
    )
    goal: str = Field(
        default="Comprehensive, fact-checked deep dive guide",
        description="Editorial goal for the generated article",
        examples=["Comprehensive, fact-checked deep dive guide"],
    )
    rough_word_target: int = Field(
        default=800,
        ge=200,
        le=5000,
        description="Approximate word count target",
        examples=[800],
    )
    template: str = Field(
        default="Hireko Editorial",
        description="HTML template layout to use",
        examples=["Hireko Editorial"],
    )
    name: str = Field(
        default="article",
        description="Subfolder name for the generated article package",
        examples=["article"],
    )
    output: Optional[str] = Field(
        default=None,
        description="Custom output directory (defaults to ./output)",
    )


class BlogGenerateResponse(BaseModel):
    """Response returned after successful blog generation."""

    success: bool
    message: str
    article_name: str
    output_dir: str
    index_url: str
    word_count: int
    iterations: int
    content_source: str = ""
    quality_score: float = 0.0
    source_quality: str = ""
    duration_seconds: float = 0.0
    article_html: str = ""
    view_url: str = ""


class ErrorResponse(BaseModel):
    """Response returned when an error occurs."""

    success: bool = False
    error: str


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str = "healthy"
    service: str = "AI Blog Generator API"
    version: str = "2.0.0"
    framework: str = "FastAPI"
    uptime_seconds: float
    server_time: str
    llm_provider: str
    llm_model: str
    output_dir: str
    dashboard_available: bool


class TemplateListResponse(BaseModel):
    """Response listing available templates."""

    templates: List[str]
    count: int


class BlogEntry(BaseModel):
    """Metadata for a single generated blog."""

    name: str
    path: str
    index_url: str
    created_at: Optional[str] = None


class BlogListResponse(BaseModel):
    """Response listing previously generated blogs."""

    blogs: List[BlogEntry]
    count: int
    output_dir: str


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Blog Generator API",
    description=(
        "REST API for generating publication-quality blog articles using AI.\n\n"
        "Features a 3-iteration pipeline: research → fact-check → render.\n\n"
        "- **POST /api/generate** — Generate a new blog\n"
        "- **GET /api/health** — Server health check\n"
        "- **GET /api/templates** — Available HTML templates\n"
        "- **GET /api/blogs** — Previously generated blogs\n"
        "- **Interactive Docs** — Visit `/docs` for Swagger UI"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/generate",
    response_model=BlogGenerateResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate a blog article",
    description="Runs the full 3-iteration blog generation pipeline: deep research, fact-check audit, and HTML rendering.",
    tags=["Blog Generation"],
)
async def generate_blog(request: BlogGenerateRequest):
    """Generate a publication-quality blog article."""

    # Validate template
    template = request.template
    if template not in TEMPLATE_CHOICES:
        template = "Hireko Editorial"

    output_dir = request.output or DEFAULT_OUTPUT_DIR

    print(f"\n[FastAPI] Received Generation Request: '{request.topic}' (Template: {template})")

    # Initialize LLM Model & Dependencies
    model = get_llm_model()
    deps = BlogAgentDeps(
        output_dir=output_dir,
        article_name=request.name,
        topic=request.topic,
        audience=request.audience_segment,
        goal=request.goal,
        word_target=request.rough_word_target,
        template_name=template,
    )

    # Run 3-Iteration Pipeline
    start_time = time.time()
    try:
        result = await run_3_iteration_blog_pipeline(deps, model=model)
        duration = round(time.time() - start_time, 2)

        # Vercel functions have temporary filesystems. Return the rendered
        # article in the response so the dashboard can open it without a DB.
        article_html = ""
        index_path = result.get("index_path")
        if index_path and os.path.isfile(index_path):
            with open(index_path, "r", encoding="utf-8") as article_file:
                article_html = article_file.read()

        if article_html:
            LATEST_GENERATED_HTML[request.name] = article_html
            LATEST_GENERATED_HTML["latest"] = article_html

        return BlogGenerateResponse(
            success=True,
            message="Blog generated successfully!",
            article_name=request.name,
            output_dir=output_dir,
            index_url=f"/output/{os.path.basename(result.get('article_folder', request.name))}/index.html",
            word_count=result.get("word_count", request.rough_word_target),
            iterations=result.get("iterations", 3),
            content_source=result.get("content_source", ""),
            quality_score=result.get("quality_score", 0.0),
            source_quality=result.get("source_quality", ""),
            duration_seconds=duration,
            article_html=article_html,
            view_url=f"/view/{request.name}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns server status, uptime, LLM configuration, and availability information.",
    tags=["System"],
)
async def health_check():
    """Check server health and configuration."""

    uptime = (datetime.now(timezone.utc) - SERVER_START_TIME).total_seconds()

    return HealthResponse(
        status="healthy",
        service="AI Blog Generator API",
        version="2.0.0",
        framework="FastAPI",
        uptime_seconds=round(uptime, 2),
        server_time=datetime.now(timezone.utc).isoformat(),
        llm_provider=os.getenv("LLM_PROVIDER", "nvidia"),
        llm_model=os.getenv("LLM_MODEL", "qwen/qwen3.7-flash"),
        output_dir=DEFAULT_OUTPUT_DIR,
        dashboard_available=os.path.isdir(DASHBOARD_DIR),
    )


@app.get(
    "/api/templates",
    response_model=TemplateListResponse,
    summary="List available templates",
    description="Returns all supported HTML blog templates.",
    tags=["Blog Generation"],
)
async def list_templates():
    """List all available blog HTML templates."""

    return TemplateListResponse(
        templates=TEMPLATE_CHOICES,
        count=len(TEMPLATE_CHOICES),
    )


@app.get(
    "/api/blogs",
    response_model=BlogListResponse,
    summary="List generated blogs",
    description="Lists all previously generated blog articles found in the output directory.",
    tags=["Blog Management"],
)
async def list_blogs():
    """List all previously generated blog articles."""

    blogs: List[BlogEntry] = []

    if os.path.isdir(DEFAULT_OUTPUT_DIR):
        for entry in sorted(os.listdir(DEFAULT_OUTPUT_DIR)):
            entry_path = os.path.join(DEFAULT_OUTPUT_DIR, entry)
            if os.path.isdir(entry_path):
                index_file = os.path.join(entry_path, "index.html")

                # Get creation time
                created_at = None
                if os.path.exists(index_file):
                    try:
                        stat = os.stat(index_file)
                        created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
                    except Exception:
                        pass

                blogs.append(
                    BlogEntry(
                        name=entry,
                        path=entry_path,
                        index_url=f"/output/{entry}/index.html",
                        created_at=created_at,
                    )
                )

    return BlogListResponse(
        blogs=blogs,
        count=len(blogs),
        output_dir=DEFAULT_OUTPUT_DIR,
    )


# ---------------------------------------------------------------------------
# Direct HTML Article Viewer Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/view/{name}",
    response_class=HTMLResponse,
    summary="View generated blog article",
    description="Returns the full, self-contained HTML page for the specified blog article with all styles and assets.",
    tags=["Blog Management"],
)
async def view_article(name: str):
    """View a generated blog directly in the browser with full styling."""
    if name in LATEST_GENERATED_HTML:
        return HTMLResponse(content=LATEST_GENERATED_HTML[name], media_type="text/html; charset=utf-8")

    candidate_dirs = [DEFAULT_OUTPUT_DIR, os.path.join(tempfile.gettempdir(), "hireko_output")]
    for out_dir in candidate_dirs:
        article_path = os.path.join(out_dir, name, "index.html")
        if os.path.isfile(article_path):
            with open(article_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), media_type="text/html; charset=utf-8")

    if "latest" in LATEST_GENERATED_HTML:
        return HTMLResponse(content=LATEST_GENERATED_HTML["latest"], media_type="text/html; charset=utf-8")

    raise HTTPException(status_code=404, detail=f"Article '{name}' not found. Please generate it first.")


@app.get(
    "/view",
    response_class=HTMLResponse,
    summary="View latest generated blog article",
    description="Returns the most recently generated blog article HTML.",
    tags=["Blog Management"],
)
async def view_latest_article():
    """View the most recently generated blog article."""
    return await view_article("latest")


# ---------------------------------------------------------------------------
# Root redirect → dashboard or docs
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to the dashboard if available, otherwise to API docs."""
    if os.path.isdir(DASHBOARD_DIR):
        return RedirectResponse(url="/dashboard/index.html")
    return RedirectResponse(url="/docs")


# ---------------------------------------------------------------------------
# Static File Mounts (must be after route definitions)
# ---------------------------------------------------------------------------

# Serve generated output files
if os.path.isdir(DEFAULT_OUTPUT_DIR):
    app.mount("/output", StaticFiles(directory=DEFAULT_OUTPUT_DIR), name="output")

# Serve blog-dashboard frontend
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def run_server(port: int = PORT):
    """Start the FastAPI server using Uvicorn."""
    print(f"\n=======================================================")
    print("AI Blog Generator — FastAPI Server Starting!")
    print(f"  API Docs (Swagger):  http://localhost:{port}/docs")
    print(f"  API Docs (ReDoc):    http://localhost:{port}/redoc")
    print(f"  OpenAPI JSON:        http://localhost:{port}/openapi.json")
    if os.path.isdir(DASHBOARD_DIR):
        print(f"  Dashboard:           http://localhost:{port}/dashboard/index.html")
    print(f"  Health Check:        http://localhost:{port}/api/health")
    print(f"=======================================================\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else PORT
    run_server(port_arg)

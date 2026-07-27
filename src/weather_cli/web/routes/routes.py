"""
Page routes (HTML rendering)
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page"""
    from ..app import templates
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "Weather CLI Pro - Route Weather Planning"}
    )


@router.get("/planner", response_class=HTMLResponse)
async def planner(request: Request):
    """Route planner page"""
    from ..app import templates
    return templates.TemplateResponse(
        request,
        "route/planner.html",
        {"title": "Route Planner"}
    )


@router.get("/compare", response_class=HTMLResponse)
async def compare(request: Request):
    """Multi-route comparison page"""
    from ..app import templates
    return templates.TemplateResponse(
        request,
        "route/compare.html",
        {"title": "Compare Routes"}
    )


@router.get("/test-upload", response_class=HTMLResponse)
async def test_upload(request: Request):
    """Test upload page for debugging"""
    from ..app import templates
    return templates.TemplateResponse(
        request,
        "route/test_upload.html",
        {"title": "Upload Test"}
    )


@router.get("/test-basic", response_class=HTMLResponse)
async def test_basic(request: Request):
    """Basic JavaScript test"""
    from ..app import templates
    return templates.TemplateResponse(
        request,
        "route/test_basic.html",
        {"title": "Basic Test"}
    )


@router.get("/test-fetch", response_class=HTMLResponse)
async def test_fetch(request: Request):
    """Fetch API test"""
    from ..app import templates
    return templates.TemplateResponse(
        request,
        "route/test_fetch.html",
        {"title": "Fetch Test"}
    )

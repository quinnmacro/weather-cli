"""
File upload endpoints
"""

import uuid
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..models.schemas import RouteUploadResponse, WaypointModel

router = APIRouter(prefix="/routes", tags=["upload"])

# In-memory route storage (use Redis in production)
_routes_store: dict = {}


@router.post("/upload", response_model=RouteUploadResponse)
async def upload_route(file: UploadFile = File(...)):
    """Upload a GPX or KML route file"""
    import sys
    print(f"[UPLOAD] Received file: {file.filename}, content_type: {file.content_type}", file=sys.stderr)

    # Validate file extension
    filename = file.filename or "route"
    ext = Path(filename).suffix.lower()
    print(f"[UPLOAD] File extension: {ext}", file=sys.stderr)

    if ext not in (".gpx", ".kml", ".kmz"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Supported: .gpx, .kml"
        )

    # Read file content
    content = await file.read()

    # Parse route
    try:
        from ...core.route import parse_gpx, parse_kml

        # Save to temp file for parsing
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Parse based on format
        if ext == ".gpx":
            route_info = parse_gpx(tmp_path)
        else:
            route_info = parse_kml(tmp_path)

        # Clean up temp file
        tmp_path.unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Generate route ID
    route_id = str(uuid.uuid4())[:8]

    # Calculate elevation gain
    elevation_gain = _calculate_elevation_gain(route_info.waypoints)

    # Store route
    _routes_store[route_id] = route_info

    # Build response - limit waypoints for display (keep original in store)
    display_waypoints = _sample_waypoints_for_display(route_info.waypoints, max_points=200)

    waypoints = [
        WaypointModel(
            lat=wp.lat,
            lon=wp.lon,
            distance_km=wp.distance_km,
            name=wp.name,
            elevation=wp.elevation
        )
        for wp in display_waypoints
    ]

    return RouteUploadResponse(
        route_id=route_id,
        name=route_info.name,
        total_distance_km=route_info.total_distance_km,
        waypoints=waypoints,
        elevation_gain_m=elevation_gain
    )


@router.get("/{route_id}")
async def get_route(route_id: str):
    """Get stored route by ID"""
    if route_id not in _routes_store:
        raise HTTPException(status_code=404, detail="Route not found")

    route_info = _routes_store[route_id]

    # Sample waypoints for display
    display_waypoints = _sample_waypoints_for_display(route_info.waypoints, max_points=500)

    return {
        "route_id": route_id,
        "name": route_info.name,
        "total_distance_km": route_info.total_distance_km,
        "waypoints": [
            {
                "lat": wp.lat,
                "lon": wp.lon,
                "distance_km": wp.distance_km,
                "elevation": wp.elevation
            }
            for wp in display_waypoints
        ]
    }


@router.post("/{route_id}/enhance")
async def enhance_route(route_id: str, activity_type: str = "hiking"):
    """Enhance route with real paths using OSRM routing.

    This adds intermediate points following actual roads/trails between waypoints.
    """
    from ...core.route import enhance_route_with_osrm

    if route_id not in _routes_store:
        raise HTTPException(status_code=404, detail="Route not found")

    route_info = _routes_store[route_id]
    original_count = len(route_info.waypoints)

    # Enhance route with OSRM
    enhanced_waypoints = enhance_route_with_osrm(
        route_info.waypoints,
        activity_type=activity_type,
        min_direct_distance_km=0.5,  # Route segments > 0.5km apart
        max_direct_distance_km=50.0
    )

    # Update route in store
    route_info.waypoints = enhanced_waypoints
    route_info.total_distance_km = enhanced_waypoints[-1].distance_km if enhanced_waypoints else 0

    # Sample for display
    display_waypoints = _sample_waypoints_for_display(enhanced_waypoints, max_points=500)

    return {
        "route_id": route_id,
        "name": route_info.name,
        "total_distance_km": route_info.total_distance_km,
        "original_waypoints": original_count,
        "enhanced_waypoints": len(enhanced_waypoints),
        "waypoints": [
            {
                "lat": wp.lat,
                "lon": wp.lon,
                "distance_km": wp.distance_km,
                "elevation": wp.elevation
            }
            for wp in display_waypoints
        ]
    }


def _calculate_elevation_gain(waypoints) -> float:
    """Calculate total elevation gain"""
    if not waypoints or len(waypoints) < 2:
        return 0.0

    gain = 0.0
    prev_elev = waypoints[0].elevation

    for wp in waypoints[1:]:
        if wp.elevation is not None and prev_elev is not None:
            if wp.elevation > prev_elev:
                gain += wp.elevation - prev_elev
        prev_elev = wp.elevation

    return gain


def get_route_from_store(route_id: str):
    """Get route from store (used by other modules)"""
    return _routes_store.get(route_id)


def _sample_waypoints_for_display(waypoints, max_points=200):
    """Sample waypoints for display to avoid too many points in browser."""
    if len(waypoints) <= max_points:
        return waypoints

    # Calculate step to evenly sample
    step = len(waypoints) / max_points
    sampled = []

    i = 0
    while len(sampled) < max_points and i < len(waypoints):
        idx = int(i)
        if idx < len(waypoints):
            sampled.append(waypoints[idx])
        i += step

    # Always include last point
    if waypoints and sampled[-1] != waypoints[-1]:
        sampled.append(waypoints[-1])

    return sampled

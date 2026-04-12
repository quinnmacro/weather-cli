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
    # Validate file extension
    filename = file.filename or "route"
    ext = Path(filename).suffix.lower()

    if ext not in (".gpx", ".kml", ".kmz"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Supported: .gpx, .kml"
        )

    # Read file content
    content = await file.read()

    # Parse route
    try:
        from ...core.route import parse_gpx, parse_kml, detect_format

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

    # Build response
    waypoints = [
        WaypointModel(
            lat=wp.lat,
            lon=wp.lon,
            distance_km=wp.distance_km,
            name=wp.name,
            elevation=wp.elevation
        )
        for wp in route_info.waypoints
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
            for wp in route_info.waypoints
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

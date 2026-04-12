"""
Weather API endpoints
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import (
    RouteAnalysisRequest,
    RouteAnalysisResponse,
    OptimalStartRequest,
    OptimalStartResponse,
    CompareRequest,
    CompareResponse,
    WaypointWeather,
    WeatherPoint,
)
from .upload import get_route_from_store

router = APIRouter(tags=["weather"])


@router.get("/point")
async def get_weather_point(
    lat: float = Query(...),
    lon: float = Query(...),
    hours: int = Query(24, ge=1, le=168)
):
    """Get hourly weather forecast for a single point"""
    from ...core import openmeteo

    points = [(lat, lon)]
    forecasts = openmeteo.get_hourly_for_route(points, hours)

    if not forecasts or not forecasts[0]:
        raise HTTPException(status_code=500, detail="Failed to fetch weather data")

    return {"hourly": forecasts[0]}


@router.post("/route")
async def get_weather_route(
    points: List[List[float]],
    hours: int = 24
):
    """Get hourly weather for multiple points"""
    from ...core import openmeteo

    if not points:
        raise HTTPException(status_code=400, detail="No points provided")

    forecasts = openmeteo.get_hourly_for_route(
        [(p[0], p[1]) for p in points],
        hours
    )

    return {"forecasts": forecasts}


@router.post("/analyze", response_model=RouteAnalysisResponse)
async def analyze_route(request: RouteAnalysisRequest):
    """Full route weather analysis with ETA calculation"""
    from ...core.route import sample_waypoints, estimate_arrival_times
    from ..services.weather_scorer import calculate_weather_score
    from ..services.wind_analysis import classify_wind

    route_info = get_route_from_store(request.route_id)
    if not route_info:
        raise HTTPException(status_code=404, detail="Route not found")

    # Sample waypoints
    sampled = sample_waypoints(route_info, interval_km=20, max_points=20)
    if not sampled:
        raise HTTPException(status_code=400, detail="No waypoints in route")

    # Set departure time
    departure = request.departure_time or datetime.now()

    # Calculate ETAs
    etas = estimate_arrival_times(sampled, request.speed_kmh, departure)

    # Fetch weather for all waypoints
    from ...core import openmeteo
    points = [(wp.lat, wp.lon) for wp in sampled]

    # Get hourly forecasts
    hours_needed = int((etas[-1][1] - departure).total_seconds() / 3600) + 24
    forecasts = openmeteo.get_hourly_for_route(points, min(168, max(72, hours_needed)))

    # Process each waypoint
    waypoint_weathers = []
    alerts = []
    total_score = 0

    for i, (wp, eta) in enumerate(etas):
        forecast = forecasts[i] if i < len(forecasts) else []
        weather = _get_weather_at_time(forecast, eta)

        # Calculate score
        score_result = calculate_weather_score(
            temp=weather.get("temp", 20),
            precipitation=weather.get("precipitation", 0),
            wind_speed=weather.get("wind_speed", 0),
            wind_direction=weather.get("wind_direction", 0),
            route_heading=_calculate_heading(sampled, i),
            activity_type=request.activity_type
        )

        # Wind classification
        wind_type = classify_wind(
            weather.get("wind_direction", 0),
            _calculate_heading(sampled, i)
        )

        wp_weather = WaypointWeather(
            waypoint={
                "lat": wp.lat,
                "lon": wp.lon,
                "distance_km": wp.distance_km,
                "name": wp.name,
                "elevation": wp.elevation
            },
            eta=eta.strftime("%Y-%m-%d %H:%M"),
            weather=WeatherPoint(
                datetime=eta.strftime("%Y-%m-%d %H:%M"),
                temp=weather.get("temp"),
                precipitation=weather.get("precipitation", 0),
                wind_speed=weather.get("wind_speed", 0),
                wind_direction=weather.get("wind_direction", 0),
                weather_code=weather.get("weather_code", 0),
            ),
            score=score_result["total"],
            wind_type=wind_type
        )
        waypoint_weathers.append(wp_weather)
        total_score += score_result["total"]

        # Generate alerts
        if weather.get("precipitation", 0) > 5:
            alerts.append(f"Heavy rain at {wp.distance_km:.0f}km ({weather.get('precipitation', 0):.1f}mm)")
        if weather.get("wind_speed", 0) > 30:
            alerts.append(f"Strong wind at {wp.distance_km:.0f}km ({weather.get('wind_speed', 0):.0f}km/h)")

    avg_score = total_score // len(waypoint_weathers) if waypoint_weathers else 0
    arrival = etas[-1][1] if etas else departure

    return RouteAnalysisResponse(
        route_id=request.route_id,
        route_name=route_info.name,
        total_distance_km=route_info.total_distance_km,
        departure_time=departure.strftime("%Y-%m-%d %H:%M"),
        estimated_arrival=arrival.strftime("%Y-%m-%d %H:%M"),
        total_time_hours=round((arrival - departure).total_seconds() / 3600, 1),
        waypoints=waypoint_weathers,
        overall_score=avg_score,
        alerts=alerts[:5]  # Limit alerts
    )


@router.post("/optimal-start", response_model=OptimalStartResponse)
async def find_optimal_start(request: OptimalStartRequest):
    """Find the best departure time"""
    from ..services.route_planner import find_optimal_departure

    route_info = get_route_from_store(request.route_id)
    if not route_info:
        raise HTTPException(status_code=404, detail="Route not found")

    search_start = request.search_start or datetime.now()
    result = await find_optimal_departure(
        route_info,
        request.speed_kmh,
        search_start,
        request.search_hours,
        request.activity_type
    )

    return OptimalStartResponse(**result)


@router.post("/compare", response_model=CompareResponse)
async def compare_routes(request: CompareRequest):
    """Compare weather across multiple routes"""
    from ..services.route_planner import compare_route_weather

    routes = []
    for route_id in request.route_ids:
        route = get_route_from_store(route_id)
        if route:
            routes.append(route)

    if len(routes) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 valid routes")

    result = await compare_route_weather(routes, request.departure_time, request.speed_kmh)
    return CompareResponse(**result)


def _get_weather_at_time(forecast: list, target_time: datetime) -> dict:
    """Get weather data closest to target time"""
    if not forecast:
        return {}

    target_str = target_time.strftime("%Y-%m-%dT%H:00")

    for point in forecast:
        if point.get("datetime", "").startswith(target_str[:13]):
            return point

    # Return closest if exact match not found
    return forecast[0] if forecast else {}


def _calculate_heading(waypoints, index: int) -> int:
    """Calculate route heading at a waypoint (degrees)"""
    import math

    if index >= len(waypoints) - 1:
        if index == 0:
            return 0  # No heading for single point
        index -= 1

    curr = waypoints[index]
    next_wp = waypoints[index + 1]

    # Calculate bearing
    lat1, lon1 = math.radians(curr.lat), math.radians(curr.lon)
    lat2, lon2 = math.radians(next_wp.lat), math.radians(next_wp.lon)

    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    return int((bearing + 360) % 360)

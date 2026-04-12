"""
Route planning services: optimal start time, route comparison
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any

from .weather_scorer import calculate_weather_score, classify_score


async def find_optimal_departure(
    route_info,
    speed_kmh: float,
    search_start: datetime,
    search_hours: int,
    activity_type: str
) -> Dict[str, Any]:
    """
    Find the best departure time within the search window.

    Evaluates each hour as a potential start time and returns
    the one with the highest average weather score.
    """
    from ..routes.weather import _get_weather_at_time, _calculate_heading
    from ...core.route import sample_waypoints, estimate_arrival_times
    from ...core import openmeteo

    # Sample waypoints
    sampled = sample_waypoints(route_info, interval_km=25, max_points=15)
    if not sampled:
        return {
            "optimal_departure": search_start.isoformat(),
            "score": 0,
            "classification": "unknown",
            "breakdown": {},
            "alternatives": []
        }

    # Fetch extended forecast (7 days)
    points = [(wp.lat, wp.lon) for wp in sampled]
    forecasts = openmeteo.get_hourly_for_route(points, hours=min(168, search_hours + 72))

    best_score = 0
    best_time = search_start
    best_breakdown = {}
    all_scores = []

    # Evaluate each potential departure hour
    for hour_offset in range(search_hours):
        departure = search_start + timedelta(hours=hour_offset)

        # Calculate ETAs for this departure time
        etas = estimate_arrival_times(sampled, speed_kmh, departure)

        # Score weather at each waypoint
        waypoint_scores = []
        score_components = {"temperature": [], "precipitation": [], "wind": []}

        for i, (wp, eta) in enumerate(etas):
            forecast = forecasts[i] if i < len(forecasts) else []
            weather = _get_weather_at_time(forecast, eta)

            result = calculate_weather_score(
                temp=weather.get("temp", 20),
                precipitation=weather.get("precipitation", 0),
                wind_speed=weather.get("wind_speed", 0),
                wind_direction=weather.get("wind_direction", 0),
                route_heading=_calculate_heading(sampled, i),
                activity_type=activity_type
            )

            waypoint_scores.append(result["total"])
            for key in score_components:
                score_components[key].append(result["breakdown"].get(key, 50))

        # Average score across route
        avg_score = sum(waypoint_scores) / len(waypoint_scores) if waypoint_scores else 0
        all_scores.append({
            "time": departure.strftime("%Y-%m-%d %H:%M"),
            "score": round(avg_score)
        })

        if avg_score > best_score:
            best_score = avg_score
            best_time = departure
            best_breakdown = {
                k: round(sum(v) / len(v)) if v else 50
                for k, v in score_components.items()
            }

    # Find top alternatives
    sorted_scores = sorted(all_scores, key=lambda x: x["score"], reverse=True)
    alternatives = sorted_scores[1:4]  # Top 3 alternatives

    return {
        "optimal_departure": best_time.strftime("%Y-%m-%d %H:%M"),
        "score": round(best_score),
        "classification": classify_score(round(best_score)),
        "breakdown": best_breakdown,
        "alternatives": alternatives
    }


async def compare_route_weather(
    routes: List,
    departure_time: datetime,
    speed_kmh: float
) -> Dict[str, Any]:
    """
    Compare weather conditions across multiple routes.

    Returns comparative analysis to help choose the best route.
    """
    from ...core.route import sample_waypoints, estimate_arrival_times
    from ...core import openmeteo
    from ..routes.weather import _get_weather_at_time, _calculate_heading

    comparisons = []

    for route in routes:
        # Sample waypoints
        sampled = sample_waypoints(route, interval_km=30, max_points=10)
        if not sampled:
            continue

        # Calculate ETAs
        etas = estimate_arrival_times(sampled, speed_kmh, departure_time)

        # Fetch weather
        points = [(wp.lat, wp.lon) for wp in sampled]
        hours = int((etas[-1][1] - departure_time).total_seconds() / 3600) + 24
        forecasts = openmeteo.get_hourly_for_route(points, min(72, hours))

        # Aggregate weather
        temps = []
        precips = []
        winds = []
        scores = []

        for i, (wp, eta) in enumerate(etas):
            forecast = forecasts[i] if i < len(forecasts) else []
            weather = _get_weather_at_time(forecast, eta)

            temps.append(weather.get("temp", 20))
            precips.append(weather.get("precipitation", 0))
            winds.append(weather.get("wind_speed", 0))

            result = calculate_weather_score(
                temp=weather.get("temp", 20),
                precipitation=weather.get("precipitation", 0),
                wind_speed=weather.get("wind_speed", 0),
                wind_direction=weather.get("wind_direction", 0),
                route_heading=_calculate_heading(sampled, i),
                activity_type="cycling"
            )
            scores.append(result["total"])

        # Calculate elevation gain
        elev_gain = _calculate_elevation_gain(route.waypoints)

        # Determine best use case
        avg_score = sum(scores) / len(scores) if scores else 0
        best_for = _determine_best_for(avg_score, sum(precips), max(winds) if winds else 0)

        comparisons.append({
            "route_id": getattr(route, "id", "unknown"),
            "route_name": route.name,
            "distance_km": route.total_distance_km,
            "elevation_gain_m": elev_gain,
            "avg_temp": round(sum(temps) / len(temps), 1) if temps else 0,
            "total_precip": round(sum(precips), 1),
            "max_wind": round(max(winds)) if winds else 0,
            "score": round(avg_score),
            "best_for": best_for
        })

    # Sort by score
    comparisons.sort(key=lambda x: x["score"], reverse=True)

    # Generate recommendation
    recommendation = _generate_recommendation(comparisons)

    return {
        "routes": comparisons,
        "recommendation": recommendation
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

    return round(gain, 1)


def _determine_best_for(score: float, total_precip: float, max_wind: float) -> str:
    """Determine what this route is best for given conditions"""
    if score >= 75 and total_precip < 5:
        return "Great for cycling"
    elif score >= 60 and max_wind < 25:
        return "Good for hiking"
    elif total_precip > 10:
        return "Indoor day"
    elif max_wind > 35:
        return "Windy - experienced riders"
    else:
        return "Moderate conditions"


def _generate_recommendation(comparisons: List[Dict]) -> str:
    """Generate recommendation text"""
    if not comparisons:
        return "No routes to compare"

    best = comparisons[0]
    if len(comparisons) == 1:
        return f"{best['route_name']} is your only option with a score of {best['score']}/100"

    diff = best["score"] - comparisons[1]["score"]
    if diff >= 15:
        return f"Strongly recommend {best['route_name']} (score {best['score']}) - significantly better conditions"
    elif diff >= 5:
        return f"Recommend {best['route_name']} (score {best['score']}) - somewhat better conditions"
    else:
        return f"Either {best['route_name']} or {comparisons[1]['route_name']} - similar conditions"

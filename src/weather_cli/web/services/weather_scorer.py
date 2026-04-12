"""
Weather scoring algorithm for route planning
"""

import math
from typing import Dict, Literal


def calculate_weather_score(
    temp: float,
    precipitation: float,
    wind_speed: float,
    wind_direction: int,
    route_heading: int,
    activity_type: Literal["cycling", "hiking", "running"] = "cycling"
) -> Dict:
    """
    Calculate weather score (0-100) for given conditions.

    Higher score = better conditions.

    Args:
        temp: Temperature in Celsius
        precipitation: Precipitation in mm
        wind_speed: Wind speed in km/h
        wind_direction: Wind direction in degrees (where wind is coming FROM)
        route_heading: Route direction in degrees (where you're going TO)
        activity_type: Type of activity (affects weighting)

    Returns:
        Dict with total score and breakdown
    """
    # Temperature score (Gaussian centered on optimal temp)
    optimal_temps = {"cycling": 20, "hiking": 18, "running": 15}
    optimal = optimal_temps.get(activity_type, 18)
    temp_score = _gaussian_score(temp, optimal=optimal, sigma=8)

    # Precipitation score (linear decrease)
    # 0mm = 100, 10mm+ = 0
    precip_score = max(0, 100 - precipitation * 10)

    # Wind score with headwind/tailwind consideration
    wind_score = _calculate_wind_score(wind_speed, wind_direction, route_heading, activity_type)

    # Weights by activity type
    weights = {
        "cycling": {"temp": 0.25, "precip": 0.25, "wind": 0.50},
        "hiking": {"temp": 0.30, "precip": 0.45, "wind": 0.25},
        "running": {"temp": 0.35, "precip": 0.35, "wind": 0.30},
    }
    w = weights.get(activity_type, weights["cycling"])

    total_score = (
        temp_score * w["temp"] +
        precip_score * w["precip"] +
        wind_score * w["wind"]
    )

    return {
        "total": round(total_score),
        "breakdown": {
            "temperature": round(temp_score),
            "precipitation": round(precip_score),
            "wind": round(wind_score),
        },
        "wind_type": _classify_wind_type(wind_direction, route_heading)
    }


def _gaussian_score(value: float, optimal: float, sigma: float) -> float:
    """Gaussian scoring function centered on optimal value"""
    return 100 * math.exp(-((value - optimal) ** 2) / (2 * sigma ** 2))


def _calculate_wind_score(
    wind_speed: float,
    wind_direction: int,
    route_heading: int,
    activity_type: str
) -> float:
    """
    Calculate wind score considering headwind/tailwind.

    Headwind significantly hurts cycling, tailwind helps.
    """
    # Calculate relative wind angle
    # wind_direction = where wind is coming FROM
    # route_heading = where you're going TO
    relative_angle = (wind_direction - route_heading + 180) % 360

    # Headwind component (0 = pure headwind, 180 = pure tailwind)
    # cos(0) = 1 for headwind, cos(180) = -1 for tailwind
    headwind_factor = math.cos(math.radians(relative_angle - 180))

    # Effective wind: positive = headwind, negative = tailwind
    effective_wind = wind_speed * headwind_factor

    # Base wind score (lower wind = better)
    base_score = max(0, 100 - wind_speed * 1.5)

    # Adjust for headwind/tailwind
    if activity_type == "cycling":
        # Cycling is most affected by wind
        if effective_wind > 0:  # Headwind
            adjustment = -effective_wind * 2
        else:  # Tailwind
            adjustment = -effective_wind * 0.5  # Small bonus for tailwind
    else:
        # Hiking/running less affected
        adjustment = -effective_wind * 0.5

    final_score = base_score + adjustment
    return max(0, min(100, final_score))


def _classify_wind_type(wind_direction: int, route_heading: int) -> str:
    """Classify wind as headwind, tailwind, or crosswind"""
    relative = abs((wind_direction - route_heading + 180) % 360 - 180)

    if relative < 45:
        return "headwind"
    elif relative > 135:
        return "tailwind"
    else:
        return "crosswind"


def classify_score(score: int) -> str:
    """Classify overall score"""
    if score >= 80:
        return "excellent"
    elif score >= 60:
        return "good"
    elif score >= 40:
        return "moderate"
    else:
        return "poor"

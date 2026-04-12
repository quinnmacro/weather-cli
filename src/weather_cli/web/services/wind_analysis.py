"""
Wind analysis utilities
"""

import math
from typing import Tuple


def classify_wind(wind_direction: int, route_heading: int) -> str:
    """
    Classify wind relative to route direction.

    Args:
        wind_direction: Where wind is coming FROM (degrees)
        route_heading: Where you're going TO (degrees)

    Returns:
        One of: 'headwind', 'tailwind', 'crosswind-left', 'crosswind-right'
    """
    # Calculate the angle wind hits you relative to your direction
    # 0 = direct headwind, 180 = direct tailwind, 90/270 = crosswind
    relative = (wind_direction - route_heading + 180) % 360

    if relative < 45 or relative > 315:
        return "headwind"
    elif 135 < relative < 225:
        return "tailwind"
    elif 45 <= relative < 135:
        return "crosswind-right"
    else:
        return "crosswind-left"


def calculate_wind_components(
    wind_speed: float,
    wind_direction: int,
    route_heading: int
) -> Tuple[float, float, str]:
    """
    Calculate headwind/crosswind components.

    Returns:
        (headwind_component, crosswind_component, classification)
        headwind_component: positive = headwind, negative = tailwind
        crosswind_component: positive = from right, negative = from left
    """
    # Relative angle (0 = wind in face, 180 = wind at back)
    relative = math.radians((wind_direction - route_heading + 180) % 360)

    headwind = wind_speed * math.cos(relative)
    crosswind = wind_speed * math.sin(relative)

    return headwind, crosswind, classify_wind(wind_direction, route_heading)


def wind_direction_to_text(degrees: int) -> str:
    """Convert wind direction in degrees to cardinal text"""
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    index = round(degrees / 22.5) % 16
    return directions[index]


def get_wind_emoji(wind_type: str) -> str:
    """Get emoji for wind type"""
    emojis = {
        "headwind": "💨↔️",  # Wind in face
        "tailwind": "💨➡️",  # Wind at back
        "crosswind-left": "💨⬅️",
        "crosswind-right": "💨➡️",
    }
    return emojis.get(wind_type, "💨")


def calculate_wind_chill(temp: float, wind_speed: float) -> float:
    """
    Calculate wind chill temperature.

    Valid for temps <= 10°C and wind > 4.8 km/h
    """
    if temp > 10 or wind_speed < 4.8:
        return temp

    # Wind chill formula (metric)
    wind_chill = (
        13.12 +
        0.6215 * temp -
        11.37 * (wind_speed ** 0.16) +
        0.3965 * temp * (wind_speed ** 0.16)
    )

    return round(wind_chill, 1)

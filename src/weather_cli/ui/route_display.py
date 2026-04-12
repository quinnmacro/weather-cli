"""
Display functions for route weather forecasts
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..config import WEATHER_CODES

console = Console()


def get_weather_emoji(code: int) -> str:
    """Get emoji for weather code"""
    return WEATHER_CODES.get(code, ("Unknown", "❓", "未知"))[1]


def get_weather_description(code: int) -> str:
    """Get description for weather code"""
    return WEATHER_CODES.get(code, ("Unknown", "❓", "未知"))[0]


def display_route_forecast(
    waypoints_data: List[Dict[str, Any]],
    route_name: str,
    total_distance_km: float,
    show_eta: bool = False,
    json_output: bool = False
):
    """Display weather forecast along a route"""
    if json_output:
        console.print_json(json.dumps(waypoints_data, indent=2, ensure_ascii=False))
        return

    title = f"🚵 Route Forecast - {route_name} ({total_distance_km:.1f} km)"

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("km", style="cyan", width=6)
    table.add_column("Date", style="white", width=12)

    if show_eta:
        table.add_column("ETA", style="yellow", width=16)

    table.add_column("Weather", width=8)
    table.add_column("Temp", style="green", width=10)
    table.add_column("Precip", style="blue", width=8)
    table.add_column("Wind", style="magenta", width=10)

    for wp_data in waypoints_data:
        row = [
            f"{wp_data['distance_km']:.0f}",
            wp_data.get("date", ""),
        ]

        if show_eta and wp_data.get("eta"):
            eta_str = wp_data["eta"]
            if isinstance(eta_str, datetime):
                eta_str = eta_str.strftime("%m/%d %H:%M")
            row.append(eta_str)

        code = wp_data.get("weather_code", 0)
        emoji = get_weather_emoji(code)

        row.extend([
            emoji,
            f"{wp_data.get('temp_max', '--')}/{wp_data.get('temp_min', '--')}°C",
            f"{wp_data.get('precipitation', 0):.1f} mm",
            f"{wp_data.get('wind_speed', '--')} km/h",
        ])

        table.add_row(*row)

    console.print(table)

    # Weather alerts
    _display_route_alerts(waypoints_data)


def _display_route_alerts(waypoints_data: List[Dict[str, Any]]):
    """Display weather alerts for the route"""
    alerts = []

    # Check for heavy rain
    rainy_points = [wp for wp in waypoints_data if wp.get("precipitation", 0) > 10]
    if rainy_points:
        distances = [f"{wp['distance_km']:.0f}km" for wp in rainy_points]
        alerts.append(f"🌧️  Heavy rain expected at: {', '.join(distances)}")

    # Check for strong winds
    windy_points = [wp for wp in waypoints_data if wp.get("wind_speed", 0) > 40]
    if windy_points:
        distances = [f"{wp['distance_km']:.0f}km" for wp in windy_points]
        alerts.append(f"💨 Strong winds (>40 km/h) at: {', '.join(distances)}")

    # Check for extreme temperatures
    cold_points = [wp for wp in waypoints_data if wp.get("temp_min", 99) < 0]
    if cold_points:
        distances = [f"{wp['distance_km']:.0f}km" for wp in cold_points]
        alerts.append(f"❄️  Freezing temperatures at: {', '.join(distances)}")

    if alerts:
        console.print()
        for alert in alerts:
            console.print(f"[yellow]{alert}[/yellow]")


def display_route_timeline(
    waypoints_data: List[Dict[str, Any]],
    route_name: str,
    total_distance_km: float
):
    """Display route forecast as a timeline"""
    console.print(f"\n[bold]📍 {route_name}[/bold] ({total_distance_km:.1f} km)\n")

    for wp_data in waypoints_data:
        distance = wp_data["distance_km"]
        code = wp_data.get("weather_code", 0)
        emoji = get_weather_emoji(code)
        desc = get_weather_description(code)
        temp = wp_data.get("temp_max", "--")
        eta = wp_data.get("eta", "")

        # Timeline marker
        if distance == 0:
            marker = "🏁"
        elif distance >= total_distance_km - 1:
            marker = "🎯"
        else:
            marker = "├─"

        eta_str = f" [{eta}]" if eta else ""
        console.print(f"  {marker} {distance:>5.0f} km: {emoji} {desc}, {temp}°C{eta_str}")


def display_route_summary(
    waypoints_data: List[Dict[str, Any]],
    route_name: str,
    total_distance_km: float
):
    """Display a summary panel for the route"""
    if not waypoints_data:
        console.print("[yellow]No weather data available[/yellow]")
        return

    # Calculate statistics
    temps = [wp.get("temp_max") for wp in waypoints_data if wp.get("temp_max") is not None]
    min_temps = [wp.get("temp_min") for wp in waypoints_data if wp.get("temp_min") is not None]
    precips = [wp.get("precipitation") for wp in waypoints_data if wp.get("precipitation") is not None]
    winds = [wp.get("wind_speed") for wp in waypoints_data if wp.get("wind_speed") is not None]

    avg_temp = sum(temps) / len(temps) if temps else 0
    min_temp = min(min_temps) if min_temps else 0
    max_temp = max(temps) if temps else 0
    total_precip = sum(precips) if precips else 0
    max_wind = max(winds) if winds else 0

    # Count weather conditions
    conditions = {}
    for wp in waypoints_data:
        code = wp.get("weather_code", 0)
        desc = get_weather_description(code)
        conditions[desc] = conditions.get(desc, 0) + 1

    most_common = max(conditions, key=conditions.get) if conditions else "Unknown"

    summary = f"""[bold]Distance:[/bold] {total_distance_km:.1f} km
[bold]Waypoints:[/bold] {len(waypoints_data)}
[bold]Temperature:[/bold] {min_temp:.0f}°C to {max_temp:.0f}°C (avg {avg_temp:.0f}°C)
[bold]Total Precipitation:[/bold] {total_precip:.1f} mm
[bold]Max Wind:[/bold] {max_wind:.0f} km/h
[bold]Most Common:[/bold] {most_common}"""

    panel = Panel(summary, title=f"🗺️ {route_name}", border_style="blue")
    console.print(panel)

"""
Rich UI components for Weather CLI
"""

import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..config import WEATHER_CODES

console = Console()


def get_weather_emoji(code: int) -> str:
    """Get emoji for weather code"""
    return WEATHER_CODES.get(code, ("Unknown", "❓", "未知"))[1]


def get_weather_description(code: int, lang: str = "en") -> str:
    """Get weather description for code"""
    info = WEATHER_CODES.get(code, ("Unknown", "❓", "未知"))
    return info[2] if lang == "zh" else info[0]


def display_current(data: Dict[str, Any], json_output: bool = False):
    """Display current weather"""
    if json_output:
        console.print_json(json.dumps(data, indent=2))
        return

    city = data.get("city", "Unknown")
    country = data.get("country", "")

    # Create title with emoji
    emoji = get_weather_emoji(data.get("weather_code", 0))
    title = Text()
    title.append(f"{emoji} {city}", style="bold cyan")
    if country:
        title.append(f" ({country})", style="dim")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    temp = data.get("temperature")
    feels = data.get("feels_like")

    table.add_row("Temperature", f"{temp}°C" if temp else "N/A")
    if feels and temp:
        diff = feels - temp
        if abs(diff) > 2:
            table.add_row("Feels Like", f"{feels}°C", style="yellow")
    table.add_row("Humidity", f"{data.get('humidity')}%")
    table.add_row("Wind", f"{data.get('wind_speed')} km/h")
    table.add_row("Pressure", f"{data.get('pressure')} hPa")
    table.add_row("Precipitation", f"{data.get('precipitation')} mm")
    table.add_row("Conditions", get_weather_description(data.get("weather_code", 0)))

    panel = Panel(table, title=title, border_style="blue")
    console.print(panel)


def display_forecast(forecast: List[Dict[str, Any]], city: str, json_output: bool = False):
    """Display forecast data"""
    if json_output:
        console.print_json(json.dumps(forecast, indent=2))
        return

    table = Table(title=f"📅 {len(forecast)}-Day Forecast - {city.capitalize()}")
    table.add_column("Date", style="cyan")
    table.add_column("Day", style="white")
    table.add_column("", style="yellow", width=3)  # Emoji
    table.add_column("Max", style="red")
    table.add_column("Min", style="blue")
    table.add_column("Precip", style="green")
    table.add_column("Wind", style="magenta")

    for day in forecast:
        emoji = get_weather_emoji(day.get("weather_code", 0))
        table.add_row(
            day["date"],
            day["day"],
            emoji,
            f"{day.get('temp_max')}°C" if day.get("temp_max") else "N/A",
            f"{day.get('temp_min')}°C" if day.get("temp_min") else "N/A",
            f"{day.get('precipitation')} mm" if day.get("precipitation") else "0 mm",
            f"{day.get('wind_speed')} km/h" if day.get("wind_speed") else "N/A",
        )

    console.print(table)


def display_history(history: List[Dict[str, Any]], city: str, json_output: bool = False):
    """Display historical weather data"""
    if json_output:
        console.print_json(json.dumps(history, indent=2))
        return

    table = Table(title=f"📊 Historical Weather - {city.capitalize()}")
    table.add_column("Date", style="cyan")
    table.add_column("Max Temp", style="red")
    table.add_column("Min Temp", style="blue")
    table.add_column("Precipitation", style="green")
    table.add_column("Max Wind", style="magenta")

    for record in history:
        table.add_row(
            record["date"],
            f"{record.get('temp_max')}°C" if record.get("temp_max") else "N/A",
            f"{record.get('temp_min')}°C" if record.get("temp_min") else "N/A",
            f"{record.get('precipitation')} mm" if record.get("precipitation") else "N/A",
            f"{record.get('wind_speed')} km/h" if record.get("wind_speed") else "N/A",
        )

    console.print(table)


def display_windy_forecast(
    forecast: List[Dict[str, Any]], city: str, model: str, json_output: bool = False
):
    """Display Windy forecast data"""
    if json_output:
        console.print_json(json.dumps(forecast, indent=2))
        return

    table = Table(title=f"🌬️ Windy Forecast ({model.upper()}) - {city.capitalize()}")
    table.add_column("Date/Time", style="cyan")
    table.add_column("Temp", style="red")
    table.add_column("Wind", style="green")
    table.add_column("Gust", style="yellow")
    table.add_column("Precip", style="blue")
    table.add_column("RH", style="magenta")

    for record in forecast:
        dt = record["datetime"].split("T")
        time_str = f"{dt[0]} {dt[1][:5]}" if len(dt) > 1 else record["datetime"]
        table.add_row(
            time_str,
            f"{record['temp']:.1f}°C" if record.get("temp") else "N/A",
            f"{record['wind_speed']:.1f} m/s" if record.get("wind_speed") else "N/A",
            f"{record['wind_gust']:.1f} m/s" if record.get("wind_gust") else "N/A",
            f"{record.get('precipitation', 0):.1f} mm",
            f"{record['humidity']:.0f}%" if record.get("humidity") else "N/A",
        )

    console.print(table)


def display_cities():
    """Display supported cities"""
    from ..config import CITIES

    table = Table(title="🌍 Supported Cities")
    table.add_column("City", style="cyan")
    table.add_column("Country", style="green")
    table.add_column("Coordinates", style="yellow")

    for city, info in CITIES.items():
        coord_str = f"{info['lat']:.2f}, {info['lon']:.2f}"
        table.add_row(city.capitalize(), info["country"], coord_str)

    console.print(table)


def display_error(message: str):
    """Display error message"""
    console.print(f"[red]Error:[/red] {message}")


def display_one_line(text: str):
    """Display one-line output"""
    console.print(text)

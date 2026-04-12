"""
Weather CLI - Main entry point
"""

import json
import sys
from datetime import datetime
from typing import Optional

import click

from . import __version__
from .config import settings, CITIES
from .core import openmeteo, get_windy_client
from .ui import (
    display_current,
    display_forecast,
    display_history,
    display_windy_forecast,
    display_cities,
    display_error,
    display_one_line,
    display_route_forecast,
    display_route_timeline,
    display_route_summary,
)


@click.group()
@click.version_option(version=__version__)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def cli(ctx: click.Context, json_output: bool):
    """Weather CLI - Professional weather command-line tool

    Get current weather, forecasts, and historical data from Open-Meteo (free)
    and Windy API.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output


@cli.command()
@click.argument("city")
@click.pass_context
def current(ctx: click.Context, city: str):
    """Get current weather for a city

    Example: weather current beijing
    """
    try:
        data = openmeteo.get_current(city)
        display_current(data, json_output=ctx.obj.get("json", False))
    except ValueError as e:
        display_error(str(e))
        sys.exit(1)
    except Exception as e:
        display_error(f"API error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option("--days", "-d", default=3, help="Number of forecast days (1-16)")
@click.pass_context
def forecast(ctx: click.Context, city: str, days: int):
    """Get weather forecast for a city

    Example: weather forecast london --days 5
    """
    try:
        data = openmeteo.get_forecast(city, days)
        display_forecast(data, city, json_output=ctx.obj.get("json", False))
    except ValueError as e:
        display_error(str(e))
        sys.exit(1)
    except Exception as e:
        display_error(f"API error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option("--start", "-s", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--end", "-e", default=None, help="End date (YYYY-MM-DD)")
@click.pass_context
def history(ctx: click.Context, city: str, start: Optional[str], end: Optional[str]):
    """Get historical weather data

    Examples:
        weather history tokyo
        weather history london -s 2026-01-01 -e 2026-01-07
    """
    try:
        data = openmeteo.get_history(city, start, end)
        display_history(data, city, json_output=ctx.obj.get("json", False))
    except ValueError as e:
        display_error(str(e))
        sys.exit(1)
    except Exception as e:
        display_error(f"API error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option(
    "--format", "-f", "fmt", default="3",
    type=click.Choice(["1", "2", "3", "4"]),
    help="Output format (1-4)"
)
def oneline(city: str, fmt: str):
    """One-line output for status bars (like wttr.in)

    Formats:
      1: 🌤️ 15°C
      2: 🌤️  🌡️15°C 🌬️10km/h
      3: Beijing: 🌤️ 15°C
      4: Beijing: 🌤️  🌡️15°C 🌬️10km/h
    """
    try:
        text = openmeteo.get_one_line(city, fmt)
        display_one_line(text)
    except ValueError as e:
        display_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option("--model", "-m", default="gfs", help="Forecast model (gfs, iconEu, arome)")
@click.option("--hours", "-h", default=24, help="Hours to forecast (1-168)")
@click.pass_context
def windy(ctx: click.Context, city: str, model: str, hours: int):
    """Get forecast from Windy API (requires API key)

    Set WINDY_API_KEY environment variable.
    Get a key at https://api.windy.com/keys

    Example: weather windy london --model gfs --hours 48
    """
    try:
        client = get_windy_client()
        data = client.get_forecast(city, model, hours)
        display_windy_forecast(data, city, model, json_output=ctx.obj.get("json", False))
    except ValueError as e:
        display_error(str(e))
        sys.exit(1)
    except Exception as e:
        display_error(f"API error: {e}")
        sys.exit(1)


@cli.command()
def cities():
    """List all supported cities"""
    display_cities()


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--type", "-t", "data_type", default="current",
    type=click.Choice(["current", "forecast"]),
    help="Type of weather data"
)
@click.pass_context
def batch(ctx: click.Context, input_file: str, data_type: str):
    """Process multiple cities from a JSON file

    Example JSON: ["beijing", "shanghai", "london"]
    """
    try:
        with open(input_file) as f:
            cities_list = json.load(f)

        if not isinstance(cities_list, list):
            display_error("Input file must contain a JSON array of city names")
            sys.exit(1)

        results = []
        for city in cities_list:
            try:
                if data_type == "current":
                    data = openmeteo.get_current(city)
                    results.append({
                        "city": city,
                        "temperature": data.get("temperature"),
                        "conditions": data.get("weather_code"),
                        "success": True,
                    })
                else:
                    data = openmeteo.get_forecast(city, 1)
                    if data:
                        results.append({
                            "city": city,
                            "temperature_max": data[0].get("temp_max"),
                            "temperature_min": data[0].get("temp_min"),
                            "success": True,
                        })
            except Exception as e:
                results.append({"city": city, "error": str(e), "success": False})

        if ctx.obj.get("json"):
            click.echo(json.dumps(results, indent=2))
        else:
            from rich.table import Table
            from rich.console import Console
            console = Console()

            table = Table(title=f"Batch Results ({data_type})")
            table.add_column("City", style="cyan")
            table.add_column("Temperature", style="green")
            table.add_column("Status", style="blue")

            for r in results:
                if r["success"]:
                    if data_type == "current":
                        temp = f"{r['temperature']}°C"
                    else:
                        temp = f"{r['temperature_max']}/{r['temperature_min']}°C"
                    table.add_row(r["city"].capitalize(), temp, "[green]OK[/green]")
                else:
                    table.add_row(r["city"].capitalize(), "N/A", f"[red]{r['error']}[/red]")

            console.print(table)

    except Exception as e:
        display_error(f"Error processing batch file: {e}")
        sys.exit(1)


@cli.command()
def config():
    """Show current configuration"""
    from rich.table import Table
    from rich.console import Console
    console = Console()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Config Dir", str(settings.config_dir))
    table.add_row("Default City", settings.default_city)
    table.add_row("Units", settings.units)
    table.add_row("Windy API Key", "Set" if settings.windy_api_key else "Not set")
    table.add_row("Forecast Days", str(settings.forecast_days))

    console.print(table)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--format", "-f", "fmt",
    type=click.Choice(["gpx", "kml", "auto"]),
    default="auto",
    help="Route file format (auto-detect by default)"
)
@click.option(
    "--interval", "-i",
    default=50,
    type=int,
    help="Distance interval (km) between weather points"
)
@click.option(
    "--speed", "-s",
    default=None,
    type=float,
    help="Average speed (km/h) for ETA estimation"
)
@click.option(
    "--departure", "-d",
    default=None,
    type=str,
    help="Departure time (YYYY-MM-DD HH:MM or 'now')"
)
@click.option(
    "--days",
    default=3,
    type=int,
    help="Forecast days (1-7)"
)
@click.option(
    "--view", "-v",
    type=click.Choice(["table", "timeline", "summary"]),
    default="table",
    help="Output view format"
)
@click.pass_context
def route(
    ctx: click.Context,
    file_path: str,
    fmt: str,
    interval: int,
    speed: Optional[float],
    departure: Optional[str],
    days: int,
    view: str
):
    """Get weather forecast along a GPX/KML route

    Parses a route file and shows weather conditions at key points.
    Optionally estimates arrival times based on your average speed.

    \b
    Examples:
        weather route hike.gpx
        weather route bike_ride.kml --interval 30
        weather route trail.gpx --speed 5 --departure "2026-04-13 08:00"
        weather route journey.gpx --view timeline
    """
    from .core.route import parse_route, sample_waypoints, estimate_arrival_times

    try:
        # Parse the route file
        route_info = parse_route(file_path, fmt)
    except ValueError as e:
        display_error(str(e))
        sys.exit(1)
    except Exception as e:
        display_error(f"Failed to parse route file: {e}")
        sys.exit(1)

    # Sample waypoints at specified intervals
    sampled = sample_waypoints(route_info, interval_km=interval, max_points=20)

    if not sampled:
        display_error("No waypoints found in route")
        sys.exit(1)

    # Calculate ETAs if speed is provided
    show_eta = False
    etas = None

    if speed and speed > 0:
        show_eta = True

        # Parse departure time
        if departure:
            if departure.lower() == "now":
                dep_time = datetime.now()
            else:
                try:
                    dep_time = datetime.strptime(departure, "%Y-%m-%d %H:%M")
                except ValueError:
                    display_error("Invalid departure time format. Use: YYYY-MM-DD HH:MM")
                    sys.exit(1)
        else:
            dep_time = datetime.now()

        try:
            etas = estimate_arrival_times(sampled, speed, dep_time)
        except ValueError as e:
            display_error(str(e))
            sys.exit(1)

    # Get coordinates for batch query
    points = [(wp.lat, wp.lon) for wp in sampled]

    try:
        # Fetch weather for all waypoints
        forecasts = openmeteo.get_forecast_batch(points, days=days)
    except Exception as e:
        display_error(f"API error: {e}")
        sys.exit(1)

    # Combine waypoint data with weather and ETA
    waypoints_data = []

    for i, wp in enumerate(sampled):
        forecast = forecasts[i] if i < len(forecasts) else []

        # Get the first day's forecast (or the day matching ETA if available)
        if show_eta and etas and i < len(etas):
            _, eta_time = etas[i]
            # Find the forecast day matching ETA
            day_forecast = _get_forecast_for_date(forecast, eta_time.date())
        else:
            day_forecast = forecast[0] if forecast else {}

        wp_data = {
            "lat": wp.lat,
            "lon": wp.lon,
            "distance_km": wp.distance_km,
            "name": wp.name,
            **day_forecast,
        }

        if show_eta and etas and i < len(etas):
            wp_data["eta"] = etas[i][1].strftime("%m/%d %H:%M")

        waypoints_data.append(wp_data)

    # Display results
    json_output = ctx.obj.get("json", False)

    if json_output:
        import json as json_mod
        from rich.console import Console
        Console().print_json(json_mod.dumps(waypoints_data, indent=2, default=str))
    elif view == "timeline":
        display_route_timeline(waypoints_data, route_info.name, route_info.total_distance_km)
    elif view == "summary":
        display_route_summary(waypoints_data, route_info.name, route_info.total_distance_km)
    else:
        display_route_forecast(
            waypoints_data,
            route_info.name,
            route_info.total_distance_km,
            show_eta=show_eta
        )


def _get_forecast_for_date(forecast: list, target_date) -> dict:
    """Get forecast for a specific date"""
    for day in forecast:
        if day.get("date") == target_date.isoformat():
            return day
    return forecast[0] if forecast else {}


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()

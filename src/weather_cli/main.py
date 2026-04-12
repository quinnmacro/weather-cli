"""
Weather CLI - Main entry point
"""

import json
import sys
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


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()

"""
Advanced meteorological analysis module
"""

import sys
from typing import Dict, List, Optional

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Pressure levels (hPa)
PRESSURE_LEVELS = [1000, 925, 850, 700, 500, 300]

# NWP Models
MODELS = {
    "gfs": {"name": "GFS", "resolution": "13km", "provider": "NOAA"},
    "ecmwf": {"name": "IFS", "resolution": "9km", "provider": "ECMWF"},
    "icon": {"name": "ICON", "resolution": "11km", "provider": "DWD"},
}

# Cities
CITIES = {
    "beijing": {"lat": 39.9042, "lon": 116.4074},
    "shanghai": {"lat": 31.2304, "lon": 121.4737},
    "guangzhou": {"lat": 23.1291, "lon": 113.2644},
    "chengdu": {"lat": 30.5728, "lon": 104.0668},
    "newyork": {"lat": 40.7128, "lon": -74.0060},
    "london": {"lat": 51.5074, "lon": -0.1278},
    "tokyo": {"lat": 35.6762, "lon": 139.6503},
    "paris": {"lat": 48.8566, "lon": 2.3522},
}


class AdvancedAPI:
    """Advanced weather analysis API"""

    GFS_URL = "https://api.open-meteo.com/v1/gfs"
    ECMWF_URL = "https://api.open-meteo.com/v1/ecmwf"
    ICON_URL = "https://api.open-meteo.com/v1/icon"

    def get_boundary_layer(self, lat: float, lon: float, model: str = "gfs") -> Dict:
        """Get boundary layer and convective parameters"""
        base_url = self.GFS_URL if model == "gfs" else self.ECMWF_URL

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "cape,convective_inhibition,lifted_index,boundary_layer_height,"
                     "freezing_level_height,temperature_2m",
            "forecast_days": 3,
        }

        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_multi_model(self, lat: float, lon: float, models: List[str] = None) -> Dict:
        """Compare multiple NWP models"""
        if models is None:
            models = ["gfs", "ecmwf"]

        results = {}
        for model in models:
            if model == "ecmwf":
                url = self.ECMWF_URL
            elif model == "icon":
                url = self.ICON_URL
            else:
                url = self.GFS_URL

            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": 7,
                "timezone": "auto",
            }

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                results[model] = response.json()
            except Exception as e:
                results[model] = {"error": str(e)}

        return results


def parse_location(location: str) -> tuple:
    """Parse location string to lat/lon"""
    if location.lower() in CITIES:
        coords = CITIES[location.lower()]
        return coords["lat"], coords["lon"]
    try:
        lat, lon = map(float, location.split(","))
        return lat, lon
    except ValueError:
        raise ValueError(f"Unknown location: {location}")


@click.group()
def cli():
    """Advanced meteorological analysis tools"""
    pass


@cli.command()
@click.argument("location")
@click.option("--model", "-m", default="gfs", help="NWP model")
def pbl(location: str, model: str):
    """Analyze boundary layer and convective parameters

    Displays: CAPE, CIN, Lifted Index, PBL height, Freezing level
    """
    try:
        lat, lon = parse_location(location)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    try:
        api = AdvancedAPI()
        data = api.get_boundary_layer(lat, lon, model)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    table = Table(title=f"Boundary Layer Analysis - {location.capitalize()}")
    table.add_column("Time", style="cyan")
    table.add_column("CAPE (J/kg)", style="red")
    table.add_column("CIN (J/kg)", style="blue")
    table.add_column("LI", style="yellow")
    table.add_column("PBL (m)", style="green")
    table.add_column("0°C Level (m)", style="magenta")

    for i in range(0, min(24, len(times)), 6):
        cape = hourly.get("cape", [0])[i] or 0
        cin = hourly.get("convective_inhibition", [0])[i] or 0
        li = hourly.get("lifted_index", [None])[i]
        pbl = hourly.get("boundary_layer_height", [None])[i]
        fl = hourly.get("freezing_level_height", [None])[i]

        table.add_row(
            times[i],
            f"{cape:.0f}",
            f"{cin:.0f}",
            f"{li:.1f}" if li else "N/A",
            f"{pbl:.0f}" if pbl else "N/A",
            f"{fl:.0f}" if fl else "N/A",
        )

    console.print(table)

    # Convective potential
    cape_vals = [v for v in hourly.get("cape", []) if v]
    max_cape = max(cape_vals) if cape_vals else 0

    if max_cape > 2500:
        potential = "[red]HIGH[/red] - Severe convection possible"
    elif max_cape > 1500:
        potential = "[yellow]MODERATE[/yellow] - Thunderstorms likely"
    elif max_cape > 500:
        potential = "[green]LOW-MODERATE[/green] - Isolated storms"
    else:
        potential = "[green]LOW[/green] - Minimal convective potential"

    console.print(f"\n[bold]Convective Potential:[/bold] {potential}")


@cli.command()
@click.argument("location")
@click.option("--models", "-m", default="gfs,ecmwf", help="Models to compare")
def compare(location: str, models: str):
    """Compare forecasts from multiple NWP models

    Example: weather-advanced compare beijing -m gfs,ecmwf,icon
    """
    try:
        lat, lon = parse_location(location)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    model_list = [m.strip() for m in models.split(",")]

    try:
        api = AdvancedAPI()
        results = api.get_multi_model(lat, lon, model_list)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)

    table = Table(title=f"Multi-Model Comparison - {location.capitalize()}")
    table.add_column("Day", style="cyan")

    for model in model_list:
        table.add_column(f"{model.upper()} Max", style="red")
        table.add_column(f"{model.upper()} Precip", style="blue")

    # Aggregate data
    days_data = {}
    for model, data in results.items():
        if "error" in data:
            continue
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        for i, date in enumerate(dates):
            if date not in days_data:
                days_data[date] = {}
            days_data[date][model] = {
                "max": daily.get("temperature_2m_max", [None])[i],
                "precip": daily.get("precipitation_sum", [None])[i],
            }

    for date in sorted(days_data.keys())[:7]:
        row = [date]
        for model in model_list:
            if model in days_data[date]:
                d = days_data[date][model]
                row.append(f"{d['max']:.1f}°C" if d['max'] else "N/A")
                row.append(f"{d['precip']:.1f}mm" if d['precip'] else "0")
            else:
                row.extend(["N/A", "N/A"])
        table.add_row(*row)

    console.print(table)


@cli.command()
def models():
    """List available NWP models"""
    table = Table(title="Available NWP Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Resolution", style="green")
    table.add_column("Provider", style="yellow")

    for model_id, info in MODELS.items():
        table.add_row(model_id, info["name"], info["resolution"], info["provider"])

    console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()

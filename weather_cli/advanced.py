#!/usr/bin/env python3
"""
Advanced Weather Analysis Module for Meteorologists

Provides:
- Atmospheric sounding (multi-level data)
- Boundary layer analysis
- Multi-model comparison
- Severe weather indices
- Synoptic analysis
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()

# Pressure levels (hPa)
PRESSURE_LEVELS = [1000, 925, 850, 700, 500, 300, 250, 200, 100]

# Available NWP models
MODELS = {
    "ecmwf_ifs": {"name": "IFS (ECMWF)", "resolution": "9km", "provider": "ECMWF"},
    "gfs": {"name": "GFS", "resolution": "13km", "provider": "NOAA"},
    "icon": {"name": "ICON", "resolution": "11km", "provider": "DWD"},
    "icon_eu": {"name": "ICON-EU", "resolution": "6km", "provider": "DWD"},
    "ukmo": {"name": "UKMO", "resolution": "10km", "provider": "Met Office"},
    "jma_gsm": {"name": "GSM (JMA)", "resolution": "55km", "provider": "JMA"},
    "meteofrance_arpege": {"name": "ARPEGE", "resolution": "7.5km", "provider": "Météo-France"},
}


class AdvancedWeatherAPI:
    """Advanced weather analysis API for meteorological research"""

    BASE_URL = "https://api.open-meteo.com/v1"
    GFS_URL = "https://api.open-meteo.com/v1/gfs"
    ECMWF_URL = "https://api.open-meteo.com/v1/ecmwf"
    ICON_URL = "https://api.open-meteo.com/v1/icon"

    def __init__(self):
        self.cities = {
            "beijing": {"lat": 39.9042, "lon": 116.4074},
            "shanghai": {"lat": 31.2304, "lon": 121.4737},
            "shenzhen": {"lat": 22.5431, "lon": 114.0579},
            "guangzhou": {"lat": 23.1291, "lon": 113.2644},
            "chengdu": {"lat": 30.5728, "lon": 104.0668},
            "xian": {"lat": 34.3416, "lon": 108.9398},
            "wuhan": {"lat": 30.5928, "lon": 114.3055},
            "nanjing": {"lat": 32.0603, "lon": 118.7969},
            "hangzhou": {"lat": 30.2741, "lon": 120.1551},
            "chongqing": {"lat": 29.4316, "lon": 106.9123},
            "kunming": {"lat": 25.0389, "lon": 102.7183},
            "shangri-la": {"lat": 27.8, "lon": 99.7},
            "newyork": {"lat": 40.7128, "lon": -74.0060},
            "london": {"lat": 51.5074, "lon": -0.1278},
            "tokyo": {"lat": 35.6762, "lon": 139.6503},
            "paris": {"lat": 48.8566, "lon": 2.3522},
            "sydney": {"lat": -33.8688, "lon": 151.2093},
        }

    def get_sounding(
        self, lat: float, lon: float, model: str = "gfs", forecast_hour: int = 0
    ) -> Dict:
        """Get atmospheric sounding data (multi-level profile)

        Args:
            lat: Latitude
            lon: Longitude
            model: NWP model (gfs, ecmwf, icon)
            forecast_hour: Forecast hour (0-384 for GFS)

        Returns:
            Dict with pressure level data for sounding analysis
        """
        # Select base URL based on model
        if model == "ecmwf":
            base_url = self.ECMWF_URL
        elif model == "icon":
            base_url = self.ICON_URL
        else:
            base_url = self.GFS_URL

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join([
                "temperature_1000hPa", "temperature_925hPa", "temperature_850hPa",
                "temperature_700hPa", "temperature_500hPa", "temperature_300hPa",
                "relative_humidity_1000hPa", "relative_humidity_850hPa", "relative_humidity_700hPa", "relative_humidity_500hPa",
                "wind_speed_1000hPa", "wind_speed_850hPa", "wind_speed_700hPa", "wind_speed_500hPa", "wind_speed_300hPa",
                "wind_direction_1000hPa", "wind_direction_850hPa", "wind_direction_700hPa", "wind_direction_500hPa",
                "geopotential_height_1000hPa", "geopotential_height_850hPa", "geopotential_height_700hPa",
                "geopotential_height_500hPa", "geopotential_height_300hPa",
            ]),
            "forecast_days": min(forecast_hour // 24 + 1, 16),
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch sounding data: {e}")

    def get_boundary_layer(
        self, lat: float, lon: float, model: str = "gfs"
    ) -> Dict:
        """Get boundary layer and convective parameters

        Returns CAPE, CIN, Lifted Index, PBL height, freezing level
        """
        base_url = self.GFS_URL if model == "gfs" else self.ECMWF_URL

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join([
                "cape",
                "convective_inhibition",
                "lifted_index",
                "boundary_layer_height",
                "freezing_level_height",
                "temperature_2m",
                "dewpoint_2m",
                "surface_pressure",
                "temperature_1000hPa", "temperature_850hPa", "temperature_700hPa", "temperature_500hPa",
            ]),
            "forecast_days": 3,
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch boundary layer data: {e}")

    def get_multi_model_forecast(
        self, lat: float, lon: float, models: List[str] = None
    ) -> Dict[str, Dict]:
        """Compare forecasts from multiple NWP models

        Args:
            lat: Latitude
            lon: Longitude
            models: List of model names to compare

        Returns:
            Dict keyed by model name with forecast data
        """
        if models is None:
            models = ["gfs", "ecmwf", "icon"]

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
                "hourly": "temperature_2m,precipitation,wind_speed_10m,pressure_msl",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": 7,
                "timezone": "auto",
            }

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                results[model] = response.json()
            except requests.RequestException:
                results[model] = {"error": f"Failed to fetch {model}"}

        return results

    def get_synoptic_pattern(
        self, lat: float, lon: float, level: int = 500
    ) -> Dict:
        """Get synoptic-scale pattern analysis

        Args:
            lat: Latitude
            lon: Longitude
            level: Pressure level for analysis (500, 700, 850, 1000)

        Returns:
            Geopotential height, vorticity, divergence data
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join([
                f"geopotential_height_{level}hPa",
                f"temperature_{level}hPa",
                f"wind_speed_{level}hPa",
                f"wind_direction_{level}hPa",
            ]),
            "forecast_days": 7,
        }

        try:
            response = requests.get(self.GFS_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch synoptic data: {e}")

    def calculate_stability_indices(
        self, sounding_data: Dict, hour_index: int = 0
    ) -> Dict:
        """Calculate atmospheric stability indices from sounding data

        Returns:
            Dict with SI, LI, TT, SWEAT, K-index calculations
        """
        hourly = sounding_data.get("hourly", {})

        # Extract temperatures at different levels
        t_1000 = hourly.get("temperature_1000hPa", [None])[hour_index]
        t_850 = hourly.get("temperature_850hPa", [None])[hour_index]
        t_700 = hourly.get("temperature_700hPa", [None])[hour_index]
        t_500 = hourly.get("temperature_500hPa", [None])[hour_index]

        # Relative humidity
        rh_850 = hourly.get("relative_humidity_850hPa", [None])[hour_index]
        rh_700 = hourly.get("relative_humidity_700hPa", [None])[hour_index]

        indices = {}

        # Lifted Index (LI) - T500 - T(parcel lifted from surface to 500hPa)
        if t_500 is not None and t_1000 is not None:
            # Simplified: assume dry adiabatic lapse rate
            parcel_t_at_500 = t_1000 - 40  # Rough approximation
            indices["lifted_index"] = t_500 - parcel_t_at_500

        # Total Totals Index (TT) = T850 + Td850 - 2*T500
        if t_850 is not None and t_500 is not None and rh_850 is not None:
            # Approximate Td from RH
            td_850 = t_850 - ((100 - rh_850) / 5)  # Simple approximation
            indices["total_totals"] = t_850 + td_850 - 2 * t_500

        # K-Index = T850 - T500 + Td850 - (T700 - Td700)
        if all(v is not None for v in [t_850, t_500, t_700, rh_850, rh_700]):
            td_850 = t_850 - ((100 - rh_850) / 5)
            td_700 = t_700 - ((100 - rh_700) / 5)
            indices["k_index"] = t_850 - t_500 + td_850 - (t_700 - td_700)

        # SWEAT Index (Severe Weather Threat)
        # SWEAT = 12*Td850 + 20*(TT-49) + 2*V850 + V500 + 125*(sin(dd500-dd850)+0.2)
        # Simplified version
        if "total_totals" in indices and indices["total_totals"] > 49:
            indices["sweat"] = 20 * (indices["total_totals"] - 49)

        # Interpretation
        indices["interpretation"] = self._interpret_stability(indices)

        return indices

    @staticmethod
    def _interpret_stability(indices: Dict) -> Dict[str, str]:
        """Interpret stability indices for weather forecasting"""
        interpretation = {}

        if "lifted_index" in indices:
            li = indices["lifted_index"]
            if li > 2:
                interpretation["lifted_index"] = "Stable"
            elif li > 0:
                interpretation["lifted_index"] = "Marginally stable"
            elif li > -2:
                interpretation["lifted_index"] = "Slightly unstable (thunderstorms possible)"
            elif li > -4:
                interpretation["lifted_index"] = "Moderately unstable (thunderstorms likely)"
            else:
                interpretation["lifted_index"] = "Very unstable (severe thunderstorms possible)"

        if "total_totals" in indices:
            tt = indices["total_totals"]
            if tt < 44:
                interpretation["total_totals"] = "No thunderstorm activity"
            elif tt < 50:
                interpretation["total_totals"] = "Isolated moderate thunderstorms"
            elif tt < 55:
                interpretation["total_totals"] = "Moderate thunderstorms possible"
            else:
                interpretation["total_totals"] = "Severe thunderstorms possible"

        if "k_index" in indices:
            k = indices["k_index"]
            if k < 20:
                interpretation["k_index"] = "Little thunderstorm potential"
            elif k < 30:
                interpretation["k_index"] = "Isolated thunderstorms"
            elif k < 40:
                interpretation["k_index"] = "Scattered thunderstorms"
            else:
                interpretation["k_index"] = "Numerous thunderstorms"

        return interpretation


# ============== CLI Commands ==============

@click.group()
def advanced():
    """Advanced meteorological analysis tools"""
    pass


@advanced.command()
@click.argument("location")
@click.option("--model", "-m", default="gfs", help="NWP model (gfs, ecmwf, icon)")
@click.option("--hour", "-h", default=0, help="Forecast hour")
def sounding(location: str, model: str, hour: int):
    """Display atmospheric sounding (multi-level profile)

    Example: weather-advanced sounding beijing --model gfs
    """
    api = AdvancedWeatherAPI()

    # Get coordinates
    if location.lower() in api.cities:
        coords = api.cities[location.lower()]
        lat, lon = coords["lat"], coords["lon"]
    else:
        try:
            lat, lon = map(float, location.split(","))
        except ValueError:
            console.print("[red]Invalid location. Use city name or 'lat,lon' format.[/red]")
            sys.exit(1)

    try:
        with console.status("[bold green]Fetching sounding data..."):
            data = api.get_sounding(lat, lon, model, hour)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    # Display sounding table
    table = Table(title=f"Atmospheric Sounding - {location.capitalize()} ({model.upper()})")
    table.add_column("Time", style="cyan")
    table.add_column("P (hPa)", style="white")
    table.add_column("T (°C)", style="red")
    table.add_column("RH (%)", style="blue")
    table.add_column("Wind", style="green")
    table.add_column("Z (m)", style="yellow")

    levels = [1000, 850, 700, 500, 300]
    time_idx = min(hour // 3, len(times) - 1) if times else 0
    time_str = times[time_idx] if times else "N/A"

    for level in levels:
        temp = hourly.get(f"temperature_{level}hPa", [None])[time_idx]
        rh = hourly.get(f"relative_humidity_{level}hPa", [None])[time_idx]
        ws = hourly.get(f"wind_speed_{level}hPa", [None])[time_idx]
        wd = hourly.get(f"wind_direction_{level}hPa", [None])[time_idx]
        z = hourly.get(f"geopotential_height_{level}hPa", [None])[time_idx]

        wind_str = f"{ws:.1f}/{wd:.0f}°" if ws and wd else "N/A"
        temp_str = f"{temp:.1f}" if temp else "N/A"
        rh_str = f"{rh:.0f}" if rh else "N/A"
        z_str = f"{z:.0f}" if z else "N/A"

        table.add_row(time_str, str(level), temp_str, rh_str, wind_str, z_str)

    console.print(table)

    # Calculate and display stability indices
    stability = api.calculate_stability_indices(data, time_idx)

    console.print("\n[bold]Stability Indices:[/bold]")
    stability_table = Table()
    stability_table.add_column("Index", style="cyan")
    stability_table.add_column("Value", style="green")
    stability_table.add_column("Interpretation", style="yellow")

    for idx, val in stability.items():
        if idx != "interpretation" and isinstance(val, (int, float)):
            interp = stability.get("interpretation", {}).get(idx, "")
            stability_table.add_row(idx.upper(), f"{val:.1f}", interp)

    console.print(stability_table)


@advanced.command()
@click.argument("location")
@click.option("--model", "-m", default="gfs", help="NWP model")
def pbl(location: str, model: str):
    """Analyze boundary layer and convective parameters

    Displays: CAPE, CIN, Lifted Index, PBL height, Freezing level
    """
    api = AdvancedWeatherAPI()

    if location.lower() in api.cities:
        coords = api.cities[location.lower()]
        lat, lon = coords["lat"], coords["lon"]
    else:
        try:
            lat, lon = map(float, location.split(","))
        except ValueError:
            console.print("[red]Invalid location[/red]")
            sys.exit(1)

    try:
        with console.status("[bold green]Analyzing boundary layer..."):
            data = api.get_boundary_layer(lat, lon, model)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    # Create summary table
    table = Table(title=f"Boundary Layer Analysis - {location.capitalize()}")
    table.add_column("Time", style="cyan")
    table.add_column("CAPE (J/kg)", style="red")
    table.add_column("CIN (J/kg)", style="blue")
    table.add_column("LI", style="yellow")
    table.add_column("PBL (m)", style="green")
    table.add_column("0°C Level (m)", style="magenta")

    # Show every 6 hours for 24 hours
    for i in range(0, min(24, len(times)), 6):
        cape = hourly.get("cape", [None])[i]
        cin = hourly.get("convective_inhibition", [None])[i]
        li = hourly.get("lifted_index", [None])[i]
        pbl = hourly.get("boundary_layer_height", [None])[i]
        fl = hourly.get("freezing_level_height", [None])[i]

        cape_str = f"{cape:.0f}" if cape else "0"
        cin_str = f"{cin:.0f}" if cin else "0"
        li_str = f"{li:.1f}" if li else "N/A"
        pbl_str = f"{pbl:.0f}" if pbl else "N/A"
        fl_str = f"{fl:.0f}" if fl else "N/A"

        table.add_row(times[i], cape_str, cin_str, li_str, pbl_str, fl_str)

    console.print(table)

    # Convective potential assessment
    cape_vals = [v for v in hourly.get("cape", []) if v]
    max_cape = max(cape_vals) if cape_vals else 0

    if max_cape > 2500:
        potential = "[red]HIGH[/red] - Severe convection possible"
    elif max_cape > 1500:
        potential = "[yellow]MODERATE[/yellow] - Thunderstorms likely"
    elif max_cape > 500:
        potential = "[green]LOW-MODERATE[/green] - Isolated storms possible"
    else:
        potential = "[green]LOW[/green] - Minimal convective potential"

    console.print(f"\n[bold]Convective Potential:[/bold] {potential}")


@advanced.command()
@click.argument("location")
@click.option("--models", "-m", default="gfs,ecmwf,icon", help="Models to compare (comma-separated)")
def compare(location: str, models: str):
    """Compare forecasts from multiple NWP models

    Example: weather-advanced compare beijing --models gfs,ecmwf,icon
    """
    api = AdvancedWeatherAPI()

    if location.lower() in api.cities:
        coords = api.cities[location.lower()]
        lat, lon = coords["lat"], coords["lon"]
    else:
        try:
            lat, lon = map(float, location.split(","))
        except ValueError:
            console.print("[red]Invalid location[/red]")
            sys.exit(1)

    model_list = [m.strip() for m in models.split(",")]

    try:
        with console.status(f"[bold green]Fetching multi-model data ({', '.join(model_list)})..."):
            results = api.get_multi_model_forecast(lat, lon, model_list)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Display comparison table
    table = Table(title=f"Multi-Model Comparison - {location.capitalize()}")
    table.add_column("Day", style="cyan")

    for model in model_list:
        table.add_column(f"{model.upper()} Max", style="red")
        table.add_column(f"{model.upper()} Precip", style="blue")

    # Get daily data for each model
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

    # Build table rows
    for date in sorted(days_data.keys()):
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

    # Model spread analysis
    console.print("\n[bold]Model Spread Analysis:[/bold]")
    for date in list(days_data.keys())[:3]:
        temps = [days_data[date][m]["max"] for m in model_list if m in days_data[date] and days_data[date][m]["max"]]
        if len(temps) >= 2:
            spread = max(temps) - min(temps)
            avg = sum(temps) / len(temps)
            console.print(f"  {date}: Avg={avg:.1f}°C, Spread={spread:.1f}°C")


@advanced.command()
@click.argument("location")
@click.option("--level", "-l", default=500, type=click.Choice(["1000", "850", "700", "500", "300"]),
              help="Pressure level (hPa)")
def synoptic(location: str, level: str):
    """Analyze synoptic-scale weather pattern

    Displays geopotential height, temperature, and wind at specified level
    """
    api = AdvancedWeatherAPI()

    if location.lower() in api.cities:
        coords = api.cities[location.lower()]
        lat, lon = coords["lat"], coords["lon"]
    else:
        try:
            lat, lon = map(float, location.split(","))
        except ValueError:
            console.print("[red]Invalid location[/red]")
            sys.exit(1)

    try:
        level_int = int(level)
        with console.status(f"[bold green]Analyzing {level_int}hPa pattern..."):
            data = api.get_synoptic_pattern(lat, lon, level_int)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    table = Table(title=f"Synoptic Analysis - {level_int}hPa - {location.capitalize()}")
    table.add_column("Time", style="cyan")
    table.add_column("Z (gpm)", style="yellow")
    table.add_column("T (°C)", style="red")
    table.add_column("Wind (m/s)", style="green")
    table.add_column("Direction", style="blue")

    # Show every 12 hours
    for i in range(0, min(72, len(times)), 12):
        z = hourly.get(f"geopotential_height_{level_int}hPa", [None])[i]
        t = hourly.get(f"temperature_{level_int}hPa", [None])[i]
        ws = hourly.get(f"wind_speed_{level_int}hPa", [None])[i]
        wd = hourly.get(f"wind_direction_{level_int}hPa", [None])[i]

        z_str = f"{z:.0f}" if z else "N/A"
        t_str = f"{t:.1f}" if t else "N/A"
        ws_str = f"{ws:.1f}" if ws else "N/A"
        wd_str = f"{wd:.0f}°" if wd else "N/A"

        table.add_row(times[i], z_str, t_str, ws_str, wd_str)

    console.print(table)

    # Flow regime analysis
    z_vals = [v for v in hourly.get(f"geopotential_height_{level_int}hPa", []) if v]
    if z_vals:
        avg_z = sum(z_vals) / len(z_vals)
        console.print(f"\n[bold]Mean Geopotential Height:[/bold] {avg_z:.0f} gpm")

        # Rough trough/ridge assessment
        if level_int == 500:
            if avg_z < 5500:
                console.print("[blue]Trough regime - cooler, unsettled weather[/blue]")
            elif avg_z > 5700:
                console.print("[red]Ridge regime - warmer, stable weather[/red]")
            else:
                console.print("[green]Zonal flow - variable weather[/green]")


@advanced.command()
@click.argument("location")
def severe(location: str):
    """Assess severe weather potential

    Analyzes CAPE, shear, and stability for severe weather prediction
    """
    api = AdvancedWeatherAPI()

    if location.lower() in api.cities:
        coords = api.cities[location.lower()]
        lat, lon = coords["lat"], coords["lon"]
    else:
        try:
            lat, lon = map(float, location.split(","))
        except ValueError:
            console.print("[red]Invalid location[/red]")
            sys.exit(1)

    try:
        with console.status("[bold green]Assessing severe weather potential..."):
            pbl_data = api.get_boundary_layer(lat, lon, "gfs")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    hourly = pbl_data.get("hourly", {})
    times = hourly.get("time", [])

    # Extract key parameters
    cape = hourly.get("cape", [])
    cin = hourly.get("convective_inhibition", [])
    li = hourly.get("lifted_index", [])

    # Create assessment table
    table = Table(title=f"Severe Weather Assessment - {location.capitalize()}")
    table.add_column("Time", style="cyan")
    table.add_column("CAPE", style="red")
    table.add_column("CIN", style="blue")
    table.add_column("LI", style="yellow")
    table.add_column("Risk Level", style="magenta")

    risk_times = []

    for i in range(0, min(48, len(times)), 3):
        c = cape[i] if i < len(cape) else 0
        ci = cin[i] if i < len(cin) else 0
        l = li[i] if i < len(li) else 0

        # Determine risk level
        if c > 2500 and l < -4:
            risk = "[red]HIGH[/red]"
        elif c > 1500 and l < -2:
            risk = "[orange1]MODERATE[/orange1]"
        elif c > 500:
            risk = "[yellow]LOW[/yellow]"
        else:
            risk = "[green]MINIMAL[/green]"

        cape_str = f"{c:.0f}" if c else "0"
        cin_str = f"{ci:.0f}" if ci else "0"
        li_str = f"{l:.1f}" if l else "N/A"

        table.add_row(times[i], cape_str, cin_str, li_str, risk)

        if c > 1500:
            risk_times.append((times[i], c, l))

    console.print(table)

    # Summary
    max_cape = max(cape) if cape else 0
    min_li = min(li) if li else 0

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Max CAPE: {max_cape:.0f} J/kg")
    console.print(f"  Min Lifted Index: {min_li:.1f}")

    if risk_times:
        console.print(f"\n[red]High-risk periods detected:[/red]")
        for t, c, l in risk_times:
            console.print(f"  {t}: CAPE={c:.0f}, LI={l:.1f}")


@advanced.command()
def models():
    """List available NWP models and their characteristics"""
    table = Table(title="Available NWP Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Resolution", style="green")
    table.add_column("Provider", style="yellow")

    for model_id, info in MODELS.items():
        table.add_row(model_id, info["name"], info["resolution"], info["provider"])

    console.print(table)

    console.print("\n[bold]Model Selection Guide:[/bold]")
    console.print("  [cyan]ecmwf_ifs[/cyan] - Best accuracy, global coverage")
    console.print("  [cyan]gfs[/cyan] - Good global coverage, longer forecast range")
    console.print("  [cyan]icon[/cyan] - Excellent for Europe")
    console.print("  [cyan]icon_eu[/cyan] - High resolution for Europe")


def main():
    advanced()


if __name__ == "__main__":
    main()

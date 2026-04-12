#!/usr/bin/env python3
"""
Weather CLI - A command-line weather application with real data sources
"""

import difflib
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import click
import requests
from rich.console import Console
from rich.table import Table

console = Console()


class WeatherAPI:
    """Weather API client supporting Open-Meteo and Windy data sources"""

    # Supported forecast models for Windy API
    WINDY_MODELS = {
        "gfs": "Global Forecast System (global)",
        "iconEu": "ICON Europe (Europe only)",
        "arome": "AROME (France only)",
        "namConus": "NAM CONUS (USA only)",
        "namHawaii": "NAM Hawaii",
        "namAlaska": "NAM Alaska",
        "gfsWave": "GFS Wave (ocean waves)",
        "cams": "CAMS (air quality)",
    }

    def __init__(self, windy_key: Optional[str] = None):
        self.windy_key = windy_key or os.environ.get("WINDY_API_KEY")
        self.windy_url = "https://api.windy.com/api/point-forecast/v2"
        self.openmeteo_url = "https://api.open-meteo.com/v1/forecast"
        self.openmeteo_archive_url = "https://archive-api.open-meteo.com/v1/archive"
        self.cities = {
            "beijing": {"lat": 39.9042, "lon": 116.4074, "timezone": "Asia/Shanghai"},
            "shanghai": {"lat": 31.2304, "lon": 121.4737, "timezone": "Asia/Shanghai"},
            "shenzhen": {"lat": 22.5431, "lon": 114.0579, "timezone": "Asia/Shanghai"},
            "newyork": {"lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
            "london": {"lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London"},
            "tokyo": {"lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
        }

    def _validate_city(self, city: str) -> str:
        """Validate city name and return lowercase version"""
        city_lower = city.lower()
        if city_lower not in self.cities:
            suggestions = self._find_similar(city_lower)
            supported = ", ".join(c.capitalize() for c in self.cities.keys())
            msg = f"City '{city}' not supported.\nSupported cities: {supported}"
            if suggestions:
                msg += f"\nDid you mean: {suggestions}?"
            raise ValueError(msg)
        return city_lower

    def _find_similar(self, city: str) -> str:
        """Find similar city names for typo suggestions"""
        matches = difflib.get_close_matches(city, self.cities.keys(), n=2, cutoff=0.6)
        return ", ".join(m.capitalize() for m in matches)

    def get_current_weather(self, city: str) -> Dict:
        """Get current weather from Open-Meteo API (free, no API key required)"""
        city_lower = self._validate_city(city)
        coords = self.cities[city_lower]

        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,pressure_msl",
            "timezone": coords["timezone"],
        }

        try:
            response = requests.get(self.openmeteo_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch weather data: {e}")

        current = data.get("current", {})
        weather_code = current.get("weather_code", 0)

        return {
            "city": city.capitalize(),
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "weather_code": weather_code,
            "weather_description": self._weather_code_to_description(weather_code),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "pressure": current.get("pressure_msl"),
            "timezone": coords["timezone"],
        }

    def get_forecast(self, city: str, days: int = 3) -> List[Dict]:
        """Get weather forecast from Open-Meteo API (free, no API key required)"""
        city_lower = self._validate_city(city)
        coords = self.cities[city_lower]

        if days < 1 or days > 7:
            raise ValueError("Days must be between 1 and 7")

        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": coords["timezone"],
            "forecast_days": days,
        }

        try:
            response = requests.get(self.openmeteo_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch forecast data: {e}")

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        forecast = []

        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i, date_str in enumerate(dates):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weather_code = daily.get("weather_code", [0])[i]

            forecast.append(
                {
                    "date": date_str,
                    "day": days_names[date_obj.weekday()],
                    "temp_max": daily.get("temperature_2m_max", [None])[i],
                    "temp_min": daily.get("temperature_2m_min", [None])[i],
                    "precipitation": daily.get("precipitation_sum", [None])[i],
                    "wind_speed": daily.get("wind_speed_10m_max", [None])[i],
                    "weather_code": weather_code,
                    "weather_description": self._weather_code_to_description(weather_code),
                }
            )

        return forecast

    def get_history(
        self, city: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict]:
        """Get historical weather data from Open-Meteo Archive API (free, no API key required)"""
        city_lower = self._validate_city(city)
        coords = self.cities[city_lower]

        today = datetime.now().date()
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_dt = today - timedelta(days=1)

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_dt = end_dt - timedelta(days=6)

        if start_dt > end_dt:
            raise ValueError("Start date must be before end date")
        if end_dt >= today:
            raise ValueError("End date must be before today (historical data only)")

        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": coords["timezone"],
        }

        try:
            response = requests.get(self.openmeteo_archive_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch historical data: {e}")

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        history = []

        for i, date_str in enumerate(dates):
            history.append(
                {
                    "date": date_str,
                    "temp_max": daily.get("temperature_2m_max", [None])[i],
                    "temp_min": daily.get("temperature_2m_min", [None])[i],
                    "precipitation": daily.get("precipitation_sum", [None])[i],
                    "wind_speed_max": daily.get("wind_speed_10m_max", [None])[i],
                }
            )

        return history

    def get_windy_forecast(
        self, city: str, model: str = "gfs", hours: int = 72
    ) -> List[Dict]:
        """Get weather forecast from Windy API

        Requires WINDY_API_KEY environment variable.
        """
        city_lower = self._validate_city(city)

        if not self.windy_key:
            raise ValueError(
                "Windy API key required. Set WINDY_API_KEY environment variable "
                "or pass windy_key parameter. Get a key at https://api.windy.com/keys"
            )

        if model not in self.WINDY_MODELS:
            raise ValueError(
                f"Invalid model '{model}'. Available: {', '.join(self.WINDY_MODELS.keys())}"
            )

        if hours < 1 or hours > 168:
            raise ValueError("Hours must be between 1 and 168 (7 days)")

        coords = self.cities[city_lower]

        payload = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "model": model,
            "parameters": ["temp", "wind", "precip", "pressure", "rh", "windGust"],
            "levels": ["surface"],
            "key": self.windy_key,
        }

        try:
            response = requests.post(self.windy_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch Windy forecast: {e}")

        forecast = []
        timestamps = data.get("ts", [])

        temp_arr = data.get("temp-surface", [])
        wind_u = data.get("wind_u-surface", [])
        wind_v = data.get("wind_v-surface", [])
        precip_arr = data.get("past3hprecip-surface", [])
        pressure_arr = data.get("pressure-surface", [])
        rh_arr = data.get("rh-surface", [])
        gust_arr = data.get("gust-surface", [])

        for i, ts in enumerate(timestamps[:hours]):
            u = wind_u[i] if i < len(wind_u) else None
            v = wind_v[i] if i < len(wind_v) else None
            wind_speed = (u**2 + v**2) ** 0.5 if u is not None and v is not None else None

            forecast.append(
                {
                    "datetime": datetime.fromtimestamp(ts / 1000).isoformat(),
                    "temp": temp_arr[i] if i < len(temp_arr) else None,
                    "wind_speed": wind_speed,
                    "wind_gust": gust_arr[i] if i < len(gust_arr) else None,
                    "precipitation": precip_arr[i] if i < len(precip_arr) else None,
                    "pressure": pressure_arr[i] if i < len(pressure_arr) else None,
                    "humidity": rh_arr[i] if i < len(rh_arr) else None,
                    "model": model,
                }
            )

        return forecast

    @staticmethod
    def _weather_code_to_description(code: int) -> str:
        """Convert WMO weather code to description"""
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return descriptions.get(code, "Unknown")


def display_current(data: Dict):
    """Display current weather data"""
    table = Table(title=f"Current Weather - {data['city']}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Temperature", f"{data['temperature']}°C")
    table.add_row("Feels Like", f"{data['feels_like']}°C")
    table.add_row("Humidity", f"{data['humidity']}%")
    table.add_row("Pressure", f"{data['pressure']} hPa")
    table.add_row("Wind", f"{data['wind_speed']} km/h at {data['wind_direction']}°")
    table.add_row("Precipitation", f"{data['precipitation']} mm")
    table.add_row("Conditions", data["weather_description"])

    console.print(table)


def display_forecast(forecast: List[Dict], city: str):
    """Display forecast data"""
    table = Table(title=f"{len(forecast)}-Day Forecast - {city.capitalize()}")
    table.add_column("Date", style="cyan")
    table.add_column("Day", style="white")
    table.add_column("Max/Min Temp", style="green")
    table.add_column("Conditions", style="yellow")
    table.add_column("Precip", style="blue")
    table.add_column("Wind", style="magenta")

    for day_data in forecast:
        temp = f"{day_data['temp_max']}°C / {day_data['temp_min']}°C"
        precip = f"{day_data['precipitation']} mm" if day_data["precipitation"] else "0 mm"
        wind = f"{day_data['wind_speed']} km/h" if day_data["wind_speed"] else "N/A"

        table.add_row(
            day_data["date"],
            day_data["day"],
            temp,
            day_data["weather_description"],
            precip,
            wind,
        )

    console.print(table)


def display_history(history: List[Dict], city: str):
    """Display historical weather data"""
    table = Table(title=f"Historical Weather - {city.capitalize()}")
    table.add_column("Date", style="cyan")
    table.add_column("Max Temp", style="red")
    table.add_column("Min Temp", style="blue")
    table.add_column("Precipitation", style="green")
    table.add_column("Max Wind", style="magenta")

    for record in history:
        temp_max = f"{record['temp_max']}°C" if record["temp_max"] is not None else "N/A"
        temp_min = f"{record['temp_min']}°C" if record["temp_min"] is not None else "N/A"
        precip = f"{record['precipitation']} mm" if record["precipitation"] is not None else "N/A"
        wind = f"{record['wind_speed_max']} km/h" if record["wind_speed_max"] is not None else "N/A"

        table.add_row(record["date"], temp_max, temp_min, precip, wind)

    console.print(table)


def display_windy_forecast(forecast: List[Dict], city: str, model: str):
    """Display Windy forecast data"""
    table = Table(title=f"Windy Forecast ({model.upper()}) - {city.capitalize()}")
    table.add_column("Date/Time", style="cyan")
    table.add_column("Temp", style="red")
    table.add_column("Wind", style="green")
    table.add_column("Gust", style="yellow")
    table.add_column("Precip", style="blue")
    table.add_column("Humidity", style="magenta")

    for record in forecast:
        dt = record["datetime"].split("T")
        time_str = f"{dt[0]} {dt[1][:5]}" if len(dt) > 1 else record["datetime"]
        temp = f"{record['temp']:.1f}°C" if record["temp"] is not None else "N/A"
        wind = f"{record['wind_speed']:.1f} m/s" if record["wind_speed"] is not None else "N/A"
        gust = f"{record['wind_gust']:.1f} m/s" if record["wind_gust"] is not None else "N/A"
        precip = f"{record['precipitation']:.1f} mm" if record["precipitation"] is not None else "0 mm"
        humidity = f"{record['humidity']:.0f}%" if record["humidity"] is not None else "N/A"

        table.add_row(time_str, temp, wind, gust, precip, humidity)

    console.print(table)


@click.group()
def cli():
    """Weather CLI - Get weather data from Open-Meteo and Windy APIs"""
    pass


@cli.command()
@click.argument("city")
def current(city: str):
    """Get current weather for a city (Open-Meteo, free)"""
    try:
        api = WeatherAPI()
        weather = api.get_current_weather(city)
        display_current(weather)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option("--days", "-d", default=3, help="Number of forecast days (1-7)")
def forecast(city: str, days: int):
    """Get weather forecast for a city (Open-Meteo, free)"""
    try:
        api = WeatherAPI()
        forecast_data = api.get_forecast(city, days)
        display_forecast(forecast_data, city)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option("--start", "-s", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--end", "-e", default=None, help="End date (YYYY-MM-DD)")
def history(city: str, start: Optional[str], end: Optional[str]):
    """Get historical weather data (Open-Meteo Archive, free)

    Examples:
        weather history beijing
        weather history london --start 2026-01-01 --end 2026-01-07
    """
    try:
        api = WeatherAPI()
        history_data = api.get_history(city, start, end)
        display_history(history_data, city)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("city")
@click.option("--model", "-m", default="gfs", help="Forecast model (gfs, iconEu, arome, etc.)")
@click.option("--hours", "-h", default=24, help="Hours to forecast (1-168)")
def windy(city: str, model: str, hours: int):
    """Get forecast from Windy API (requires API key)

    Set WINDY_API_KEY environment variable.
    Get a key at https://api.windy.com/keys

    Models: gfs (global), iconEu (Europe), arome (France), namConus (USA)

    Examples:
        weather windy beijing
        weather windy london --model iconEu --hours 48
    """
    try:
        api = WeatherAPI()
        forecast_data = api.get_windy_forecast(city, model, hours)
        display_windy_forecast(forecast_data, city, model)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)


@cli.command("models")
def list_models():
    """List available Windy forecast models"""
    api = WeatherAPI()
    table = Table(title="Windy Forecast Models")
    table.add_column("Model", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Coverage", style="yellow")

    coverage_map = {
        "gfs": "Global",
        "iconEu": "Europe",
        "arome": "France",
        "namConus": "USA",
        "namHawaii": "Hawaii",
        "namAlaska": "Alaska",
        "gfsWave": "Global Oceans",
        "cams": "Global",
    }

    for model, desc in api.WINDY_MODELS.items():
        coverage = coverage_map.get(model, "Unknown")
        table.add_row(model, desc, coverage)

    console.print(table)
    console.print("\n[yellow]Note:[/yellow] ECMWF is not available in Windy API (licensing restrictions)")


@cli.command()
def cities():
    """List all supported cities"""
    api = WeatherAPI()
    table = Table(title="Supported Cities")
    table.add_column("City", style="cyan")
    table.add_column("Coordinates", style="green")
    table.add_column("Timezone", style="yellow")

    for city, info in api.cities.items():
        coord_str = f"Lat: {info['lat']}, Lon: {info['lon']}"
        table.add_row(city.capitalize(), coord_str, info["timezone"])

    console.print(table)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--type", "-t", "data_type", default="current",
              type=click.Choice(["current", "forecast", "history"]),
              help="Type of weather data to fetch")
def batch(input_file: str, data_type: str):
    """Process multiple cities from a JSON file

    Example JSON file: ["beijing", "shanghai", "london"]
    """
    try:
        with open(input_file, "r") as f:
            cities_list = json.load(f)

        if not isinstance(cities_list, list):
            console.print("[red]Error: Input file must contain a JSON array of city names[/red]")
            sys.exit(1)

        api = WeatherAPI()
        results = []

        for city in cities_list:
            try:
                if data_type == "current":
                    data = api.get_current_weather(city)
                    results.append({
                        "city": city,
                        "temperature": f"{data['temperature']}°C",
                        "conditions": data["weather_description"],
                        "success": True,
                    })
                elif data_type == "forecast":
                    data = api.get_forecast(city, 1)
                    if data:
                        results.append({
                            "city": city,
                            "temperature": f"{data[0]['temp_max']}/{data[0]['temp_min']}°C",
                            "conditions": data[0]["weather_description"],
                            "success": True,
                        })
                else:
                    data = api.get_history(city)
                    if data:
                        results.append({
                            "city": city,
                            "temperature": f"{data[-1]['temp_max']}/{data[-1]['temp_min']}°C",
                            "conditions": f"Precip: {data[-1]['precipitation']}mm",
                            "success": True,
                        })
            except Exception as e:
                results.append({"city": city, "error": str(e), "success": False})

        table = Table(title=f"Batch Results ({data_type})")
        table.add_column("City", style="cyan")
        table.add_column("Temperature", style="green")
        table.add_column("Conditions", style="yellow")
        table.add_column("Status", style="blue")

        for result in results:
            if result["success"]:
                table.add_row(
                    result["city"].capitalize(),
                    result["temperature"],
                    result["conditions"],
                    "[green]OK[/green]",
                )
            else:
                table.add_row(
                    result["city"].capitalize(),
                    "N/A",
                    "N/A",
                    f"[red]Error: {result['error']}[/red]",
                )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error processing batch file: {e}[/red]")
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()

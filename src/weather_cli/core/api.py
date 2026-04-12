"""
Weather API clients for multiple data sources
"""

import difflib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from ..config import CITIES


class BaseAPIClient:
    """Base class for weather API clients"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "weather-cli/0.2.0"})

    def _validate_city(self, city: str) -> str:
        """Validate city name and return lowercase version"""
        city_lower = city.lower()
        if city_lower not in CITIES:
            suggestions = self._find_similar(city_lower)
            supported = ", ".join(c.capitalize() for c in CITIES.keys())
            msg = f"City '{city}' not supported.\nSupported cities: {supported}"
            if suggestions:
                msg += f"\nDid you mean: {suggestions}?"
            raise ValueError(msg)
        return city_lower

    @staticmethod
    def _find_similar(city: str) -> str:
        """Find similar city names for typo suggestions"""
        matches = difflib.get_close_matches(city, CITIES.keys(), n=2, cutoff=0.6)
        return ", ".join(m.capitalize() for m in matches)


class OpenMeteoClient(BaseAPIClient):
    """Client for Open-Meteo API (free, no API key required)"""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def get_current(self, city: str) -> Dict[str, Any]:
        """Get current weather"""
        city_lower = self._validate_city(city)
        coords = CITIES[city_lower]

        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "precipitation,weather_code,wind_speed_10m,wind_direction_10m,"
                       "pressure_msl",
            "timezone": coords["timezone"],
        }

        response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        return {
            "city": city.capitalize(),
            "country": coords["country"],
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "weather_code": current.get("weather_code", 0),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "pressure": current.get("pressure_msl"),
            "fetched_at": datetime.now().isoformat(),
        }

    def get_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """Get weather forecast"""
        city_lower = self._validate_city(city)
        coords = CITIES[city_lower]

        if days < 1 or days > 16:
            raise ValueError("Days must be between 1 and 16")

        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,wind_speed_10m_max,uv_index_max",
            "timezone": coords["timezone"],
            "forecast_days": days,
        }

        response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        forecast = []

        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i, date_str in enumerate(dates):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            forecast.append({
                "date": date_str,
                "day": days_names[date_obj.weekday()],
                "temp_max": daily.get("temperature_2m_max", [None])[i],
                "temp_min": daily.get("temperature_2m_min", [None])[i],
                "precipitation": daily.get("precipitation_sum", [None])[i],
                "wind_speed": daily.get("wind_speed_10m_max", [None])[i],
                "uv_index": daily.get("uv_index_max", [None])[i],
                "weather_code": daily.get("weather_code", [0])[i],
            })

        return forecast

    def get_history(
        self, city: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get historical weather data"""
        city_lower = self._validate_city(city)
        coords = CITIES[city_lower]

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
            raise ValueError("End date must be before today")

        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                    "wind_speed_10m_max",
            "timezone": coords["timezone"],
        }

        response = self.session.get(self.ARCHIVE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        history = []

        for i, date_str in enumerate(dates):
            history.append({
                "date": date_str,
                "temp_max": daily.get("temperature_2m_max", [None])[i],
                "temp_min": daily.get("temperature_2m_min", [None])[i],
                "precipitation": daily.get("precipitation_sum", [None])[i],
                "wind_speed": daily.get("wind_speed_10m_max", [None])[i],
            })

        return history

    def get_one_line(self, city: str, format_str: str = "3") -> str:
        """Get one-line weather output (similar to wttr.in format)"""
        data = self.get_current(city)
        code = data.get("weather_code", 0)

        from ..config import WEATHER_CODES
        weather_info = WEATHER_CODES.get(code, ("Unknown", "❓", "未知"))
        emoji = weather_info[1]
        temp = data.get("temperature", "N/A")

        # Format patterns (similar to wttr.in)
        if format_str == "1":
            return f"{emoji} {temp}°C"
        elif format_str == "2":
            return f"{emoji}  🌡️{temp}°C 🌬️{data.get('wind_speed', 0)}km/h"
        elif format_str == "3":
            return f"{city.capitalize()}: {emoji} {temp}°C"
        elif format_str == "4":
            return f"{city.capitalize()}: {emoji}  🌡️{temp}°C 🌬️{data.get('wind_speed', 0)}km/h"
        else:
            return f"{emoji} {temp}°C"


class WindyClient(BaseAPIClient):
    """Client for Windy API (requires API key)"""

    URL = "https://api.windy.com/api/point-forecast/v2"

    MODELS = {
        "gfs": "Global Forecast System",
        "iconEu": "ICON Europe",
        "arome": "AROME France",
        "namConus": "NAM USA",
    }

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        super().__init__(timeout)
        self.api_key = api_key

    def get_forecast(
        self, city: str, model: str = "gfs", hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get forecast from Windy API"""
        if not self.api_key:
            raise ValueError(
                "Windy API key required. Set WINDY_API_KEY environment variable. "
                "Get a key at https://api.windy.com/keys"
            )

        city_lower = self._validate_city(city)
        coords = CITIES[city_lower]

        if model not in self.MODELS:
            raise ValueError(f"Invalid model '{model}'. Available: {', '.join(self.MODELS.keys())}")

        if hours < 1 or hours > 168:
            raise ValueError("Hours must be between 1 and 168")

        payload = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "model": model,
            "parameters": ["temp", "wind", "precip", "pressure", "rh", "windGust"],
            "levels": ["surface"],
            "key": self.api_key,
        }

        response = self.session.post(self.URL, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        forecast = []
        timestamps = data.get("ts", [])

        temp_arr = data.get("temp-surface", [])
        wind_u = data.get("wind_u-surface", [])
        wind_v = data.get("wind_v-surface", [])
        gust_arr = data.get("gust-surface", [])
        precip_arr = data.get("past3hprecip-surface", [])
        rh_arr = data.get("rh-surface", [])

        for i, ts in enumerate(timestamps[:hours]):
            u = wind_u[i] if i < len(wind_u) else None
            v = wind_v[i] if i < len(wind_v) else None
            wind_speed = (u**2 + v**2) ** 0.5 if u is not None and v is not None else None

            forecast.append({
                "datetime": datetime.fromtimestamp(ts / 1000).isoformat(),
                "temp": temp_arr[i] if i < len(temp_arr) else None,
                "wind_speed": wind_speed,
                "wind_gust": gust_arr[i] if i < len(gust_arr) else None,
                "precipitation": precip_arr[i] if i < len(precip_arr) else None,
                "humidity": rh_arr[i] if i < len(rh_arr) else None,
                "model": model,
            })

        return forecast


# Convenience instances
openmeteo = OpenMeteoClient()


def get_windy_client(api_key: Optional[str] = None) -> WindyClient:
    """Get Windy client with optional API key override"""
    from ..config import settings
    return WindyClient(api_key or settings.windy_api_key)

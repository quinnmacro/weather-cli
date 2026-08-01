# Weather CLI Pro

> 专业命令行天气应用，支持多数据源与气象分析

A professional command-line weather application with real data sources and advanced meteorological analysis.

## Features

- **Multiple Data Sources**: Open-Meteo (free, no API key) and Windy API
- **Current & Forecast**: Real-time weather and multi-day forecasts
- **Historical Data**: Archive weather data queries
- **Advanced Meteorology**: Boundary layer analysis, multi-model comparison
- **JSON Output**: Machine-readable output for scripting
- **One-line Format**: Status bar friendly output (like wttr.in)

## Project Structure

```
weather-cli/
├── src/weather_cli/
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── advanced.py       # Advanced meteorology commands
│   ├── config/
│   │   └── settings.py   # Configuration & weather codes
│   ├── core/
│   │   └── api.py        # API clients (OpenMeteo, Windy)
│   └── ui/
│       └── display.py    # Rich terminal display
├── tests/
│   └── test_api.py
├── pyproject.toml
└── README.md
```

## Data Sources

| Command | Source | API Key | Data Type |
|---------|--------|---------|-----------|
| `current` | Open-Meteo | Free, no key | Real-time |
| `forecast` | Open-Meteo | Free, no key | Forecast |
| `history` | Open-Meteo Archive | Free, no key | Historical |
| `windy` | Windy API | Required | Forecast |

## Installation

```bash
pip install -e .
```

## Basic Usage

```bash
# Current weather
weather current beijing

# Forecast
weather forecast london --days 5

# Historical weather
weather history tokyo --start 2026-01-01 --end 2026-01-07

# One-line output (for status bars)
weather oneline beijing

# JSON output
weather --json current beijing

# Windy forecast (requires API key)
export WINDY_API_KEY=your_key
weather windy beijing --hours 48

# List supported cities
weather cities
```

## Advanced Analysis (for Meteorologists)

```bash
weather-advanced pbl shanghai          # Boundary layer analysis
weather-advanced compare tokyo         # Multi-model comparison
weather-advanced models                # List NWP models
```

### Boundary Layer Analysis
- CAPE (Convective Available Potential Energy)
- CIN (Convective Inhibition)
- Lifted Index
- PBL Height
- Freezing Level

### Multi-Model Comparison
Compare GFS, ECMWF IFS, ICON forecasts for ensemble analysis.

## Configuration

Config file: `~/.config/weather-cli/.env`

```bash
WEATHER_DEFAULT_CITY=beijing
WEATHER_UNITS=metric
WEATHER_FORECAST_DAYS=3
WINDY_API_KEY=your_key
```

## Supported Cities

Beijing, Shanghai, Shenzhen, Guangzhou, Chengdu, Xi'an, Wuhan, Nanjing, Hangzhou, Chongqing, Kunming, Shangri-La, New York, London, Tokyo, Paris, Sydney

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
ruff check src tests
```

## License

MIT

---

<sub>Last updated: 2026-08-01 · Status: 🟡 Maintenance</sub>

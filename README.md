# Weather CLI

A command-line weather application with real data sources and advanced meteorological analysis.

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

# Windy forecast (requires API key)
export WINDY_API_KEY=your_key
weather windy beijing --hours 48
```

---

## Advanced Analysis (for Meteorologists)

```bash
weather-advanced sounding beijing --model gfs
weather-advanced pbl shanghai
weather-advanced compare tokyo --models gfs,ecmwf,icon
weather-advanced synoptic london --level 500
weather-advanced severe guangzhou
weather-advanced models
```

### Atmospheric Sounding
Multi-level temperature, humidity, wind, and geopotential height profile.

### Boundary Layer Analysis
- CAPE (Convective Available Potential Energy)
- CIN (Convective Inhibition)
- Lifted Index
- PBL Height
- Freezing Level

### Multi-Model Comparison
Compare GFS, ECMWF IFS, ICON forecasts for ensemble analysis.

### Synoptic Pattern
Geopotential height, temperature, wind at standard pressure levels (1000-300 hPa).

### Severe Weather Assessment
Convective potential and severe weather risk analysis.

---

## Supported Cities

Beijing, Shanghai, Shenzhen, Guangzhou, Chengdu, Xi'an, Wuhan, Nanjing, Hangzhou, Chongqing, Kunming, Shangri-La, New York, London, Tokyo, Paris, Sydney

## License

MIT

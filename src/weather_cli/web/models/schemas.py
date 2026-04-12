"""
Pydantic models for API request/response
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class WaypointModel(BaseModel):
    """Waypoint along a route"""
    lat: float
    lon: float
    distance_km: float = 0.0
    name: str = ""
    elevation: Optional[float] = None


class RouteUploadResponse(BaseModel):
    """Response after uploading a route file"""
    route_id: str
    name: str
    total_distance_km: float
    waypoints: List[WaypointModel]
    elevation_gain_m: Optional[float] = None


class BreakPointModel(BaseModel):
    """Break point / rest stop"""
    distance_km: float
    duration_minutes: int
    name: str = ""


class RouteAnalysisRequest(BaseModel):
    """Request for route weather analysis"""
    route_id: str
    departure_time: Optional[datetime] = None
    speed_kmh: float = 15.0
    breaks: List[BreakPointModel] = []
    activity_type: str = "cycling"  # cycling, hiking, running


class WeatherPoint(BaseModel):
    """Weather data for a single point/time"""
    datetime: str
    temp: Optional[float] = None
    feels_like: Optional[float] = None
    precipitation: float = 0.0
    precipitation_probability: float = 0.0
    wind_speed: float = 0.0
    wind_direction: int = 0
    wind_gust: float = 0.0
    weather_code: int = 0
    humidity: float = 0.0


class WaypointWeather(BaseModel):
    """Weather data for a waypoint with ETA"""
    waypoint: WaypointModel
    eta: str
    weather: WeatherPoint
    score: int = 0
    wind_type: str = ""  # headwind, tailwind, crosswind


class RouteAnalysisResponse(BaseModel):
    """Full route analysis response"""
    route_id: str
    route_name: str
    total_distance_km: float
    departure_time: str
    estimated_arrival: str
    total_time_hours: float
    waypoints: List[WaypointWeather]
    overall_score: int
    alerts: List[str]


class OptimalStartRequest(BaseModel):
    """Request for optimal start time calculation"""
    route_id: str
    speed_kmh: float = 15.0
    search_start: Optional[datetime] = None
    search_hours: int = 48
    activity_type: str = "cycling"


class OptimalStartResponse(BaseModel):
    """Optimal start time result"""
    optimal_departure: str
    score: int
    classification: str
    breakdown: dict
    alternatives: List[dict]


class CompareRequest(BaseModel):
    """Request for multi-route comparison"""
    route_ids: List[str]
    departure_time: datetime
    speed_kmh: float = 15.0


class RouteComparison(BaseModel):
    """Comparison data for a single route"""
    route_id: str
    route_name: str
    distance_km: float
    elevation_gain_m: float
    avg_temp: float
    total_precip: float
    max_wind: float
    score: int
    best_for: str


class CompareResponse(BaseModel):
    """Multi-route comparison response"""
    routes: List[RouteComparison]
    recommendation: str

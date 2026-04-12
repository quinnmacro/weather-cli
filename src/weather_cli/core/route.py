"""
Route file parsing and waypoint extraction
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from geopy.distance import geodesic


@dataclass
class Waypoint:
    """A point along a route"""
    lat: float
    lon: float
    distance_km: float = 0.0  # Distance from route start
    name: str = ""
    elevation: Optional[float] = None


@dataclass
class RouteInfo:
    """Parsed route information"""
    name: str
    total_distance_km: float
    waypoints: List[Waypoint] = field(default_factory=list)


def parse_gpx(file_path: Path) -> RouteInfo:
    """Parse GPX file and extract route information"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            gpx = __import__("gpxpy").parse(f)
    except Exception as e:
        raise ValueError(f"Failed to parse GPX file: {e}")

    all_points: List[Waypoint] = []
    route_name = file_path.stem

    # Extract from tracks
    for track in gpx.tracks:
        if track.name:
            route_name = track.name
        for segment in track.segments:
            for point in segment.points:
                all_points.append(Waypoint(
                    lat=point.latitude,
                    lon=point.longitude,
                    elevation=point.elevation,
                ))

    # Extract from routes (if no tracks)
    if not all_points:
        for route in gpx.routes:
            if route.name:
                route_name = route.name
            for point in route.points:
                all_points.append(Waypoint(
                    lat=point.latitude,
                    lon=point.longitude,
                    elevation=point.elevation,
                ))

    # Extract from waypoints (if no tracks/routes)
    if not all_points:
        for wpt in gpx.waypoints:
            all_points.append(Waypoint(
                lat=wpt.latitude,
                lon=wpt.longitude,
                elevation=wpt.elevation,
                name=wpt.name or "",
            ))

    if not all_points:
        raise ValueError("No track points, route points, or waypoints found in GPX file")

    # Calculate cumulative distances
    waypoints = _calculate_distances(all_points)

    return RouteInfo(
        name=route_name,
        total_distance_km=waypoints[-1].distance_km if waypoints else 0,
        waypoints=waypoints,
    )


def parse_kml(file_path: Path) -> RouteInfo:
    """Parse KML file and extract route information"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            doc = f.read()
    except Exception as e:
        raise ValueError(f"Failed to read KML file: {e}")

    try:
        kml_obj = __import__("fastkml").kml.KML()
        kml_obj.from_string(doc)
    except Exception as e:
        raise ValueError(f"Failed to parse KML file: {e}")

    all_points: List[Waypoint] = []
    route_name = file_path.stem

    def process_feature(feature):
        nonlocal route_name, all_points

        if hasattr(feature, "name") and feature.name:
            route_name = feature.name

        if hasattr(feature, "geometry"):
            geom = feature.geometry
            if geom is not None:
                coords = _extract_coords_from_geometry(geom)
                for lon, lat in coords:
                    all_points.append(Waypoint(lat=lat, lon=lon))

        # Process nested features
        if hasattr(feature, "features"):
            for f in feature.features:
                process_feature(f)

        if hasattr(feature, "document"):
            process_feature(feature.document)

    for feature in kml_obj.features:
        process_feature(feature)

    if not all_points:
        raise ValueError("No coordinates found in KML file")

    waypoints = _calculate_distances(all_points)

    return RouteInfo(
        name=route_name,
        total_distance_km=waypoints[-1].distance_km if waypoints else 0,
        waypoints=waypoints,
    )


def _extract_coords_from_geometry(geom) -> List[Tuple[float, float]]:
    """Extract coordinates from KML geometry"""
    coords = []

    # Point
    if hasattr(geom, "coords"):
        for coord in geom.coords:
            coords.append((coord[0], coord[1]))  # lon, lat

    # LineString
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            coords.extend(_extract_coords_from_geometry(g))

    return coords


def _calculate_distances(points: List[Waypoint]) -> List[Waypoint]:
    """Calculate cumulative distance for each waypoint"""
    if not points:
        return []

    result = [Waypoint(
        lat=points[0].lat,
        lon=points[0].lon,
        distance_km=0.0,
        name=points[0].name,
        elevation=points[0].elevation,
    )]

    for i in range(1, len(points)):
        prev = result[-1]
        curr = points[i]

        # Calculate distance from previous point
        dist = geodesic(
            (prev.lat, prev.lon),
            (curr.lat, curr.lon)
        ).kilometers

        result.append(Waypoint(
            lat=curr.lat,
            lon=curr.lon,
            distance_km=prev.distance_km + dist,
            name=curr.name,
            elevation=curr.elevation,
        ))

    return result


def sample_waypoints(
    route: RouteInfo,
    interval_km: float = 50,
    max_points: int = 20
) -> List[Waypoint]:
    """Sample waypoints at regular intervals along the route"""
    if not route.waypoints:
        return []

    if route.total_distance_km <= interval_km:
        # Short route - return start, middle, end
        mid_idx = len(route.waypoints) // 2
        points = [route.waypoints[0]]
        if mid_idx > 0 and mid_idx < len(route.waypoints) - 1:
            points.append(route.waypoints[mid_idx])
        if len(route.waypoints) > 1:
            points.append(route.waypoints[-1])
        return points[:max_points]

    sampled = [route.waypoints[0]]  # Always include start
    next_distance = interval_km

    for wp in route.waypoints[1:]:
        if wp.distance_km >= next_distance:
            sampled.append(wp)
            next_distance += interval_km

        if len(sampled) >= max_points - 1:
            break

    # Always include end point if different from last sampled
    if sampled[-1].distance_km < route.total_distance_km - 1:
        sampled.append(route.waypoints[-1])

    return sampled


def estimate_arrival_times(
    waypoints: List[Waypoint],
    avg_speed_kmh: float,
    departure_time: datetime
) -> List[Tuple[Waypoint, datetime]]:
    """Calculate estimated arrival time for each waypoint"""
    if avg_speed_kmh <= 0:
        raise ValueError("Average speed must be positive")

    result = [(waypoints[0], departure_time)]

    for i in range(1, len(waypoints)):
        prev_wp, prev_time = result[-1]
        curr_wp = waypoints[i]

        # Distance from previous waypoint
        dist_km = curr_wp.distance_km - prev_wp.distance_km

        # Time to travel this distance
        hours = dist_km / avg_speed_kmh
        eta = prev_time + timedelta(hours=hours)

        result.append((curr_wp, eta))

    return result


def detect_format(file_path: Path) -> str:
    """Detect file format from extension"""
    ext = file_path.suffix.lower()
    if ext == ".gpx":
        return "gpx"
    elif ext in (".kml", ".kmz"):
        return "kml"
    else:
        raise ValueError(f"Unknown file format: {ext}. Supported: .gpx, .kml")


def parse_route(file_path: str, format: str = "auto") -> RouteInfo:
    """Parse route file with auto-detection"""
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    if format == "auto":
        format = detect_format(path)

    if format == "gpx":
        return parse_gpx(path)
    elif format == "kml":
        return parse_kml(path)
    else:
        raise ValueError(f"Unsupported format: {format}")

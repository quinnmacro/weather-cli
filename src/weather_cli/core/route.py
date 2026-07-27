"""
Route file parsing and waypoint extraction
"""

import requests
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


# OSRM profile mapping for different activities
OSRM_PROFILES = {
    "cycling": "bike",      # Uses cycling routes
    "hiking": "foot",       # Uses walking/hiking paths
    "running": "foot",      # Uses walking paths
    "driving": "car",       # Uses driving roads
}


def get_osrm_route(
    start_lon: float, start_lat: float,
    end_lon: float, end_lat: float,
    profile: str = "foot"
) -> Optional[List[Tuple[float, float]]]:
    """Get route from OSRM (Open Source Routing Machine).

    Args:
        start_lon, start_lat: Starting coordinates
        end_lon, end_lat: Ending coordinates
        profile: Routing profile (foot, bike, car)

    Returns:
        List of (lon, lat) coordinates along the route, or None if failed
    """
    # OSRM demo server (free, no API key needed)
    # Use public routing server
    base_url = f"https://router.project-osrm.org/route/v1/{profile}"

    # Format: longitude,latitude
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"

    url = f"{base_url}/{coords}"
    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok":
            return None

        # Extract coordinates from GeoJSON
        coordinates = data["routes"][0]["geometry"]["coordinates"]
        return [(lon, lat) for lon, lat in coordinates]

    except Exception as e:
        print(f"OSRM routing failed: {e}")
        return None


def enhance_route_with_osrm(
    waypoints: List[Waypoint],
    activity_type: str = "hiking",
    min_direct_distance_km: float = 0.5,
    max_direct_distance_km: float = 50.0
) -> List[Waypoint]:
    """Enhance route by getting actual paths between waypoints using OSRM.

    Only routes between points that are far apart (to avoid too many API calls).

    Args:
        waypoints: Original waypoints
        activity_type: Type of activity (cycling, hiking, running)
        min_direct_distance_km: Only route if direct distance > this value (default 0.5km)
        max_direct_distance_km: Maximum distance to route (default 50km)

    Returns:
        Enhanced waypoints with actual paths
    """
    if len(waypoints) < 2:
        return waypoints

    profile = OSRM_PROFILES.get(activity_type, "foot")
    enhanced = []

    for i, wp in enumerate(waypoints):
        enhanced.append(wp)

        if i < len(waypoints) - 1:
            next_wp = waypoints[i + 1]

            # Calculate direct distance
            direct_dist = geodesic(
                (wp.lat, wp.lon),
                (next_wp.lat, next_wp.lon)
            ).kilometers

            # Only use OSRM if points are far apart (and not too far for reasonable routing)
            if min_direct_distance_km < direct_dist <= max_direct_distance_km:
                route_coords = get_osrm_route(
                    wp.lon, wp.lat,
                    next_wp.lon, next_wp.lat,
                    profile
                )

                if route_coords and len(route_coords) > 2:
                    # Add intermediate points from OSRM route (skip first and last)
                    for lon, lat in route_coords[1:-1]:
                        enhanced.append(Waypoint(
                            lat=lat,
                            lon=lon,
                            elevation=None,
                            name=""
                        ))

    # Recalculate distances
    return _calculate_distances(enhanced)


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

    all_points: List[Waypoint] = []
    route_name = file_path.stem

    # Use xml.etree for KML parsing (more reliable than fastkml for simple KML)
    import xml.etree.ElementTree as ET

    # Remove namespace for easier parsing
    doc_clean = doc
    for ns in ['xmlns="http://www.opengis.net/kml/2.2"', "xmlns='http://www.opengis.net/kml/2.2'"]:
        doc_clean = doc_clean.replace(ns, '')

    try:
        root = ET.fromstring(doc_clean)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse KML XML: {e}")

    # Find document name
    name_elem = root.find('.//name')
    if name_elem is not None and name_elem.text:
        route_name = name_elem.text

    # Find LineString coordinates
    for coords_elem in root.findall('.//coordinates'):
        if coords_elem.text:
            coords_text = coords_elem.text.strip()
            for coord_pair in coords_text.split():
                parts = coord_pair.split(',')
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        elev = float(parts[2]) if len(parts) > 2 else None
                        all_points.append(Waypoint(lat=lat, lon=lon, elevation=elev))
                    except ValueError:
                        continue

    # Also check for Point elements (waypoints)
    for point in root.findall('.//Point/coordinates'):
        if point.text:
            parts = point.text.strip().split(',')
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                    all_points.append(Waypoint(lat=lat, lon=lon))
                except ValueError:
                    continue

    if not all_points:
        raise ValueError(f"No coordinates found in KML file")

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


def interpolate_waypoints(
    waypoints: List[Waypoint],
    max_segment_distance_km: float = 0.1
) -> List[Waypoint]:
    """Interpolate waypoints to make the route smoother.

    Adds intermediate points between waypoints that are far apart,
    so the route doesn't appear as straight lines on the map.

    Args:
        waypoints: Original waypoints
        max_segment_distance_km: Maximum distance between consecutive points (default 100m)

    Returns:
        Interpolated waypoints with more points
    """
    if len(waypoints) < 2:
        return waypoints

    interpolated = []

    for i, wp in enumerate(waypoints):
        interpolated.append(wp)

        if i < len(waypoints) - 1:
            next_wp = waypoints[i + 1]

            # Calculate distance to next waypoint
            dist = geodesic(
                (wp.lat, wp.lon),
                (next_wp.lat, next_wp.lon)
            ).kilometers

            # Add intermediate points if distance > threshold
            if dist > max_segment_distance_km:
                num_points = int(dist / max_segment_distance_km)

                for j in range(1, num_points):
                    # Linear interpolation
                    t = j / num_points

                    new_lat = wp.lat + t * (next_wp.lat - wp.lat)
                    new_lon = wp.lon + t * (next_wp.lon - wp.lon)

                    # Interpolate elevation
                    if wp.elevation is not None and next_wp.elevation is not None:
                        new_elev = wp.elevation + t * (next_wp.elevation - wp.elevation)
                    else:
                        new_elev = None

                    interpolated.append(Waypoint(
                        lat=new_lat,
                        lon=new_lon,
                        elevation=new_elev,
                        name=""
                    ))

    # Recalculate distances
    return _calculate_distances(interpolated)


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

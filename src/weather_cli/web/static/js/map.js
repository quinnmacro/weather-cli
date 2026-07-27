/**
 * Map initialization - using Leaflet (works without WebGL)
 */

let map = null;
let routeLayer = null;
let markersLayer = null;

/**
 * Initialize the map with route
 */
function initMap(waypoints) {
    console.log('initMap called with', waypoints.length, 'waypoints');

    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.error('Map container not found');
        return;
    }

    const lats = waypoints.map(wp => wp.lat);
    const lons = waypoints.map(wp => wp.lon);

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    const centerLat = (minLat + maxLat) / 2;
    const centerLon = (minLon + maxLon) / 2;

    console.log('Center:', centerLat, centerLon);

    // Check if Leaflet is available
    if (typeof L === 'undefined') {
        console.error('Leaflet not loaded');
        mapContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;"><p>Map unavailable - Leaflet library not loaded</p></div>';
        return;
    }

    // Create map if not exists
    if (!map) {
        map = L.map('map').setView([centerLat, centerLon], 12);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);

        // Add scale control
        L.control.scale({ metric: true, imperial: false }).addTo(map);
    }

    // Clear existing route and markers
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    if (markersLayer) {
        map.removeLayer(markersLayer);
    }

    // Create route line
    const coords = waypoints.map(wp => [wp.lat, wp.lon]);
    routeLayer = L.polyline(coords, {
        color: '#3b82f6',
        weight: 4,
        opacity: 0.8
    }).addTo(map);

    // Fit bounds
    map.fitBounds(routeLayer.getBounds(), { padding: [30, 30] });

    // Create markers layer
    markersLayer = L.layerGroup().addTo(map);

    // Add start marker
    const startIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #10b981; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">S</div>',
        iconSize: [28, 28],
        iconAnchor: [14, 14]
    });
    L.marker([waypoints[0].lat, waypoints[0].lon], { icon: startIcon })
        .bindPopup('<b>Start</b><br>' + waypoints[0].lat.toFixed(4) + ', ' + waypoints[0].lon.toFixed(4))
        .addTo(markersLayer);

    // Add end marker
    const last = waypoints[waypoints.length - 1];
    const endIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #ef4444; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">E</div>',
        iconSize: [28, 28],
        iconAnchor: [14, 14]
    });
    L.marker([last.lat, last.lon], { icon: endIcon })
        .bindPopup('<b>End</b><br>' + last.lat.toFixed(4) + ', ' + last.lon.toFixed(4))
        .addTo(markersLayer);

    // Add intermediate waypoint markers (every 5th point)
    waypoints.forEach((wp, i) => {
        if (i > 0 && i < waypoints.length - 1 && i % 5 === 0) {
            L.circleMarker([wp.lat, wp.lon], {
                radius: 5,
                fillColor: '#f59e0b',
                color: 'white',
                weight: 2,
                fillOpacity: 0.9
            })
            .bindPopup(wp.distance_km.toFixed(1) + ' km')
            .addTo(markersLayer);
        }
    });

    console.log('Map initialized successfully');
}

function getWeatherEmoji(code) {
    const codes = {
        0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
        45: '🌫️', 48: '🌫️',
        51: '🌧️', 53: '🌧️', 55: '🌧️',
        61: '🌧️', 63: '🌧️', 65: '🌧️',
        71: '🌨️', 73: '🌨️', 75: '❄️',
        80: '🌦️', 81: '🌦️', 82: '⛈️',
        95: '⛈️', 96: '⛈️', 99: '⛈️'
    };
    return codes[code] || '❓';
}

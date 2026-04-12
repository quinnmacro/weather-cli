/**
 * MapLibre GL map initialization
 */

let map = null;
let routeLayer = null;
let markersLayer = null;

/**
 * Initialize the map with route
 */
function initMap(waypoints) {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;

    // Calculate bounds
    const lats = waypoints.map(wp => wp.lat);
    const lons = waypoints.map(wp => wp.lon);
    const center = [
        (Math.min(...lons) + Math.max(...lons)) / 2,
        (Math.min(...lats) + Math.max(...lats)) / 2
    ];

    // Initialize map if not exists
    if (!map) {
        map = new maplibregl.Map({
            container: 'map',
            style: 'https://demotiles.maplibre.org/style.json',
            center: center,
            zoom: 10
        });

        map.addControl(new maplibregl.NavigationControl(), 'top-right');
    } else {
        map.setCenter(center);
    }

    // Convert waypoints to GeoJSON
    const geojson = {
        type: 'FeatureCollection',
        features: [{
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: waypoints.map(wp => [wp.lon, wp.lat])
            },
            properties: {
                name: 'Route'
            }
        }]
    };

    // Remove existing layers
    if (map.getLayer('route')) map.removeLayer('route');
    if (map.getSource('route')) map.removeSource('route');

    // Add route source and layer
    map.on('load', () => {
        map.addSource('route', {
            type: 'geojson',
            data: geojson
        });

        map.addLayer({
            id: 'route',
            type: 'line',
            source: 'route',
            paint: {
                'line-color': '#3b82f6',
                'line-width': 4,
                'line-opacity': 0.8
            }
        });

        // Fit bounds
        const bounds = new maplibregl.LngLatBounds();
        waypoints.forEach(wp => bounds.extend([wp.lon, wp.lat]));
        map.fitBounds(bounds, { padding: 50 });

        // Add markers for start and end
        if (waypoints.length > 0) {
            // Start marker
            new maplibregl.Marker({ color: '#10b981' })
                .setLngLat([waypoints[0].lon, waypoints[0].lat])
                .setPopup(new maplibregl.Popup().setText('Start'))
                .addTo(map);

            // End marker
            const last = waypoints[waypoints.length - 1];
            new maplibregl.Marker({ color: '#ef4444' })
                .setLngLat([last.lon, last.lat])
                .setPopup(new maplibregl.Popup().setText('End'))
                .addTo(map);
        }
    });
}

/**
 * Add waypoint markers to map
 */
function addWaypointMarkers(waypoints, weatherData) {
    if (!map) return;

    // Remove existing waypoint markers
    document.querySelectorAll('.waypoint-marker').forEach(el => el.remove());

    waypoints.forEach((wp, i) => {
        if (i === 0 || i === waypoints.length - 1) return; // Skip start/end

        const weather = weatherData[i];
        if (!weather) return;

        // Create custom marker element
        const el = document.createElement('div');
        el.className = 'waypoint-marker';
        el.innerHTML = `
            <div class="bg-white rounded-full p-1 shadow-md text-xs">
                ${getWeatherEmoji(weather.weather_code)}
            </div>
        `;

        new maplibregl.Marker(el)
            .setLngLat([wp.lon, wp.lat])
            .setPopup(new maplibregl.Popup().setHTML(`
                <strong>${wp.distance_km.toFixed(0)} km</strong><br>
                Temp: ${weather.temp?.toFixed(0) || '--'}°C<br>
                Precip: ${weather.precipitation?.toFixed(1) || 0} mm
            `))
            .addTo(map);
    });
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

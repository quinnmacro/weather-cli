/**
 * Chart.js configurations for weather visualization
 */

let tempChart = null;
let precipChart = null;
let elevationChart = null;

/**
 * Draw temperature chart
 */
function drawTempChart(waypoints) {
    const ctx = document.getElementById('tempChart');
    if (!ctx) return;

    if (tempChart) tempChart.destroy();

    const labels = waypoints.map(wp => wp.waypoint.distance_km.toFixed(0) + ' km');
    const temps = waypoints.map(wp => wp.weather.temp);
    const feelsLike = waypoints.map(wp => wp.weather.feels_like || wp.weather.temp);

    tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Temperature (°C)',
                data: temps,
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                fill: true,
                tension: 0.3
            }, {
                label: 'Feels Like (°C)',
                data: feelsLike,
                borderColor: '#f97316',
                borderDash: [5, 5],
                fill: false,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: {
                    title: { display: true, text: '°C' }
                }
            }
        }
    });
}

/**
 * Draw precipitation chart
 */
function drawPrecipChart(waypoints) {
    const ctx = document.getElementById('precipChart');
    if (!ctx) return;

    if (precipChart) precipChart.destroy();

    const labels = waypoints.map(wp => wp.waypoint.distance_km.toFixed(0) + ' km');
    const precip = waypoints.map(wp => wp.weather.precipitation || 0);

    precipChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Precipitation (mm)',
                data: precip,
                backgroundColor: precip.map(p => p > 5 ? '#3b82f6' : p > 0 ? '#93c5fd' : '#e5e7eb'),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'mm' }
                }
            }
        }
    });
}

/**
 * Draw elevation profile
 */
function drawElevationChart(waypoints) {
    const ctx = document.getElementById('elevationChart');
    if (!ctx) return;

    if (elevationChart) elevationChart.destroy();

    const labels = waypoints.map(wp => wp.distance_km.toFixed(0) + ' km');
    const elevations = waypoints.map(wp => wp.elevation || 0);

    elevationChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Elevation (m)',
                data: elevations,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                fill: true,
                tension: 0.1,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    title: { display: true, text: 'm' }
                }
            }
        }
    });
}

/**
 * PCCS4 Climate tile — outside/fridge temps, wind, rain, conditions, min/max.
 */
(function () {
    'use strict';

    const API_WEATHER_INTERVAL_MS = 300000;
    const SENSOR_POLL_INTERVAL_MS = 5000;

    const els = {
        outside: document.getElementById('temp-outside'),
        fridge: document.getElementById('temp-fridge'),
        range: document.getElementById('temp-range'),
        humidity: document.getElementById('temp-humidity'),
        weatherIcon: document.getElementById('climate-weather-icon'),
        summary: document.getElementById('weather-summary'),
        wind: document.getElementById('weather-wind'),
        rain: document.getElementById('weather-rain'),
        lowTonight: document.getElementById('weather-low-tonight'),
    };

    if (!els.outside) return;

    const home = window.pccs4Location;
    let lat = home?.latitude ?? -37.191;
    let lng = home?.longitude ?? 145.711;
    let sensorOutside = null;
    let sensorFridge = null;

    function formatTemp(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '—°C';
        }
        return `${Math.round(Number(value))}°C`;
    }

    function formatHumidity(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '—%';
        }
        return `${Math.round(Number(value))}%`;
    }

    function formatWind(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '— km/h';
        }
        return `${Math.round(Number(value))} km/h`;
    }

    function formatPercent(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '—%';
        }
        return `${Math.round(Number(value))}%`;
    }

    function formatRange(min, max) {
        const hasMin = min !== null && min !== undefined && !Number.isNaN(Number(min));
        const hasMax = max !== null && max !== undefined && !Number.isNaN(Number(max));
        if (!hasMin && !hasMax) return '—° / —°';
        const minText = hasMin ? `${Math.round(Number(min))}°` : '—°';
        const maxText = hasMax ? `${Math.round(Number(max))}°` : '—°';
        return `${minText} / ${maxText}`;
    }

    function getWeatherIcon(code, isDay) {
        const icons = {
            0: isDay ? 'fa-sun' : 'fa-moon',
            1: isDay ? 'fa-cloud-sun' : 'fa-cloud-moon',
            2: 'fa-cloud',
            3: 'fa-cloud',
            45: 'fa-smog',
            48: 'fa-smog',
            51: 'fa-cloud-rain',
            53: 'fa-cloud-rain',
            55: 'fa-cloud-rain',
            61: 'fa-cloud-showers-heavy',
            63: 'fa-cloud-showers-heavy',
            65: 'fa-cloud-showers-heavy',
            71: 'fa-snowflake',
            73: 'fa-snowflake',
            75: 'fa-snowflake',
            80: 'fa-cloud-showers-heavy',
            81: 'fa-cloud-showers-heavy',
            82: 'fa-cloud-showers-heavy',
            95: 'fa-bolt',
            96: 'fa-bolt',
            99: 'fa-bolt',
        };
        return icons[Number(code)] || 'fa-cloud';
    }

    function applyWeatherIcon(code, isDay) {
        if (!els.weatherIcon || code === null || code === undefined) return;
        const icon = getWeatherIcon(code, Boolean(isDay));
        els.weatherIcon.className = `fa-solid ${icon} tile__icon`;
    }

    function applySensorTemps(data) {
        if (!data) return;

        if (data.outside_temp_c != null) {
            sensorOutside = data.outside_temp_c;
        } else if (data.temp_c != null) {
            sensorOutside = data.temp_c;
        }

        if (data.fridge_temp_c != null) {
            sensorFridge = data.fridge_temp_c;
        }

        if (sensorOutside != null && els.outside) {
            els.outside.textContent = formatTemp(sensorOutside);
        }

        if (sensorFridge != null && els.fridge) {
            els.fridge.textContent = formatTemp(sensorFridge);
        } else if (data.fridge_temp_c == null && els.fridge && sensorFridge == null) {
            els.fridge.textContent = '—°C';
        }
    }

    function updateWeatherData(data) {
        if (!data) return;

        if (data.summary !== undefined && els.summary) {
            els.summary.textContent = data.summary || '—';
        }

        const wind = data.wind_kmh ?? data.wind_speed;
        if (wind !== undefined && els.wind) {
            els.wind.textContent = formatWind(wind);
        }

        const rain = data.rain_chance_percent ?? data.precipitation_probability ?? data.rain_chance;
        if (rain !== undefined && els.rain) {
            els.rain.textContent = formatPercent(rain);
        }

        const low = data.low_tonight_c ?? data.low_tonight ?? data.overnight_low;
        if (low !== undefined && els.lowTonight) {
            els.lowTonight.textContent = formatTemp(low);
        }

        const code = data.weather_code ?? data.code;
        const isDay = data.is_day ?? data.isDay;
        if (code !== undefined) {
            applyWeatherIcon(code, isDay);
        }

        const humidity = data.humidity_percent ?? data.humidity ?? data.relative_humidity;
        if (humidity !== undefined && els.humidity) {
            els.humidity.textContent = formatHumidity(humidity);
        }

        if ((data.temp_min !== undefined || data.temp_max !== undefined) && els.range) {
            els.range.textContent = formatRange(data.temp_min, data.temp_max);
        }
    }

    function setLocation(newLat, newLng) {
        if (typeof newLat !== 'number' || typeof newLng !== 'number') return;
        lat = newLat;
        lng = newLng;
        fetchApiWeather();
    }

    async function fetchApiWeather() {
        try {
            const res = await fetch('/api/weather', { cache: 'no-store' });
            if (!res.ok) return false;
            update(await res.json());
            return true;
        } catch {
            return false;
        }
    }

    async function fetchSensors() {
        try {
            const res = await fetch('/api/sensors', { cache: 'no-store' });
            if (!res.ok) return;
            onSensorUpdate(await res.json());
        } catch {
            /* socket will deliver sensor_update */
        }
    }

    function update(data) {
        if (!data) return;

        if (typeof data.latitude === 'number' && typeof data.longitude === 'number') {
            lat = data.latitude;
            lng = data.longitude;
        }

        applySensorTemps(data);

        if (sensorOutside == null) {
            const forecastOutside = data.temperature_c ?? data.outside_temp ?? data.temp;
            if (forecastOutside !== undefined && els.outside) {
                els.outside.textContent = formatTemp(forecastOutside);
            }
        }

        updateWeatherData(data);
    }

    function onSensorUpdate(data) {
        if (!data) return;
        applySensorTemps(data);
    }

    fetchSensors();
    fetchApiWeather();
    setInterval(fetchSensors, SENSOR_POLL_INTERVAL_MS);
    setInterval(fetchApiWeather, API_WEATHER_INTERVAL_MS);

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.climate = {
        update,
        onSensorUpdate,
        setLocation,
        refreshSensors: fetchSensors,
        refreshApiWeather: fetchApiWeather,
        refreshWeather: fetchApiWeather,
    };

    window.climateTile = window.PCCS4.climate;
    window.temperatureTile = window.PCCS4.climate;
    window.weatherTile = window.PCCS4.climate;
})();
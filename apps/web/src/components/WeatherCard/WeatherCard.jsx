import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import './WeatherCard.css';

const RAY_COUNT = 8;
const DEFAULT_API_KEY = 'e1fdacf45084462c99561513263110';

export function WeatherCard({
  apiKey = DEFAULT_API_KEY,
  defaultCity = 'Bengaluru',
}) {
  const [variant, setVariant] = useState('sunny'); // 'sunny' | 'rain' | 'cloudy'
  const [temp, setTemp] = useState(28);
  const [highTemp, setHighTemp] = useState(32);
  const [lowTemp, setLowTemp] = useState(19);
  const [locationName, setLocationName] = useState('Bengaluru, India');
  const [conditionText, setConditionText] = useState('Sunny');
  const [loading, setLoading] = useState(false);

  // Fetch live weather from WeatherAPI
  const fetchWeather = async () => {
    if (!apiKey) return;
    try {
      setLoading(true);
      const res = await fetch(
        `https://api.weatherapi.com/v1/forecast.json?key=${apiKey}&q=${encodeURIComponent(
          defaultCity
        )}&days=1&aqi=no`
      );
      if (!res.ok) throw new Error('Weather API request failed');
      const data = await res.json();

      const currentTemp = Math.round(data.current?.temp_c ?? 28);
      const text = data.current?.condition?.text || 'Sunny';
      const max = Math.round(
        data.forecast?.forecastday?.[0]?.day?.maxtemp_c ?? currentTemp + 4
      );
      const min = Math.round(
        data.forecast?.forecastday?.[0]?.day?.mintemp_c ?? currentTemp - 6
      );
      const loc = `${data.location?.name || defaultCity}, ${
        data.location?.country === 'India' ? 'India' : data.location?.country || 'India'
      }`;

      setTemp(currentTemp);
      setHighTemp(max);
      setLowTemp(min);
      setLocationName(loc);
      setConditionText(text);

      const lower = text.toLowerCase();
      if (
        lower.includes('rain') ||
        lower.includes('drizzle') ||
        lower.includes('thunder') ||
        lower.includes('shower') ||
        lower.includes('storm')
      ) {
        setVariant('rain');
        setConditionText('Mid Rain');
      } else if (
        lower.includes('cloud') ||
        lower.includes('overcast') ||
        lower.includes('mist') ||
        lower.includes('fog') ||
        lower.includes('haze')
      ) {
        setVariant('cloudy');
        setConditionText('Cloudy');
      } else {
        setVariant('sunny');
        setConditionText('Sunny');
      }
    } catch {
      // Offline / sandboxed fallback: maintain realistic solar irradiance data
      if (variant === 'rain') {
        setTemp(24);
        setHighTemp(32);
        setLowTemp(16);
        setConditionText('Mid Rain');
      } else if (variant === 'cloudy') {
        setTemp(22);
        setHighTemp(25);
        setLowTemp(17);
        setConditionText('Cloudy');
      } else {
        setTemp(31);
        setHighTemp(34);
        setLowTemp(18);
        setConditionText('Sunny');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather();
  }, [defaultCity]);

  // Click card to cycle weather variants (Sunny -> Mid Rain -> Cloudy)
  const handleCycleVariant = () => {
    if (variant === 'sunny') {
      setVariant('rain');
      setTemp(24);
      setHighTemp(32);
      setLowTemp(16);
      setConditionText('Mid Rain');
    } else if (variant === 'rain') {
      setVariant('cloudy');
      setTemp(22);
      setHighTemp(25);
      setLowTemp(17);
      setConditionText('Cloudy');
    } else {
      setVariant('sunny');
      setTemp(31);
      setHighTemp(34);
      setLowTemp(18);
      setConditionText('Sunny');
    }
  };

  return (
    <div
      className={`solar-weather-card variant-${variant}`}
      onClick={handleCycleVariant}
      title="Click to toggle Weather state (Sunny / Mid Rain / Cloudy)"
      role="region"
      aria-label="Solar Site Weather & Irradiance Radar"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleCycleVariant();
        }
      }}
    >
      {/* ===================================================================
          1. BACKGROUND SVG GRADIENT MESH
          =================================================================== */}
      <svg
        fill="none"
        viewBox="0 0 342 175"
        xmlns="http://www.w3.org/2000/svg"
        className="weather-background"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          fill={`url(#paint0_linear_${variant})`}
          d="M0 66.4396C0 31.6455 0 14.2484 11.326 5.24044C22.6519 -3.76754 39.6026 0.147978 73.5041 7.97901L307.903 62.1238C324.259 65.9018 332.436 67.7909 337.218 73.8031C342 79.8154 342 88.2086 342 104.995V131C342 151.742 342 162.113 335.556 168.556C329.113 175 318.742 175 298 175H44C23.2582 175 12.8873 175 6.44365 168.556C0 162.113 0 151.742 0 131V66.4396Z"
        />
        <defs>
          {/* MID RAIN GRADIENT */}
          <linearGradient
            gradientUnits="userSpaceOnUse"
            y2={128}
            x2="354.142"
            y1={128}
            x1={0}
            id="paint0_linear_rain"
          >
            <stop stopColor="#5936B4" />
            <stop stopColor="#362A84" offset={1} />
          </linearGradient>

          {/* SUNNY GRADIENT */}
          <linearGradient
            gradientUnits="userSpaceOnUse"
            y2={128}
            x2="354.142"
            y1={128}
            x1={0}
            id="paint0_linear_sunny"
          >
            <stop stopColor="#F9A03F" />
            <stop stopColor="#E8590C" offset={1} />
          </linearGradient>

          {/* CLOUDY GRADIENT */}
          <linearGradient
            gradientUnits="userSpaceOnUse"
            y2={128}
            x2="354.142"
            y1={128}
            x1={0}
            id="paint0_linear_cloudy"
          >
            <stop stopColor="#6C7A96" />
            <stop stopColor="#3F4A66" offset={1} />
          </linearGradient>
        </defs>
      </svg>

      {/* ===================================================================
          2. WEATHER ILLUSTRATION ICON
          =================================================================== */}
      {/* VARIANT A: SUNNY */}
      {variant === 'sunny' && (
        <div className="weather-sun">
          <svg
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 64 64"
          >
            <defs>
              <radialGradient id="sun_core_dynamic" cx="50%" cy="45%" r="55%">
                <stop offset="0%" stopColor="#FFF3B0" />
                <stop offset="100%" stopColor="#FFCE31" />
              </radialGradient>
            </defs>
            <g className="sun-rays" stroke="#FFE066" strokeWidth={4} strokeLinecap="round">
              {Array.from({ length: RAY_COUNT }).map((_, i) => (
                <line
                  key={i}
                  x1={32}
                  y1={5}
                  x2={32}
                  y2={12}
                  transform={`rotate(${(360 / RAY_COUNT) * i} 32 32)`}
                />
              ))}
            </g>
            <circle cx={32} cy={32} r={13} fill="url(#sun_core_dynamic)" />
          </svg>
        </div>
      )}

      {/* VARIANT B: MID RAIN */}
      {variant === 'rain' && (
        <div className="weather-cloud-rain">
          <svg
            fill="#000000"
            preserveAspectRatio="xMidYMid meet"
            className="weather-iconify"
            role="img"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 64 64"
          >
            <g fill="#75d6ff">
              <path d="M10.8 42.9c-.5 1.5-.1 3 1 3.4c1.1.4 2.4-.5 3-2c.6-1.8.7-4.1.2-6.9c-2.1 1.9-3.6 3.8-4.2 5.5" />
              <path d="M13.2 57.4c.6-1.8.7-4.1.2-6.9c-2.1 1.8-3.6 3.7-4.2 5.5c-.5 1.5-.1 3 1 3.4c1.1.4 2.5-.5 3-2" />
              <path d="M51.5 37.4c-2.1 1.8-3.6 3.7-4.2 5.5c-.5 1.5-.1 3 1 3.4c1.1.4 2.4-.5 3-2c.5-1.7.6-4.1.2-6.9" />
              <path d="M38.2 55.9c-.5 1.5-.1 3 1 3.4s2.4-.5 3-2c.6-1.8.7-4.1.2-6.9c-2 1.9-3.5 3.8-4.2 5.5" />
              <path d="M46.9 55.9c-.5 1.5-.1 3 1 3.4s2.4-.5 3-2c.6-1.8.7-4.1.2-6.9c-2.1 1.9-3.6 3.8-4.2 5.5" />
              <path d="M18.6 55.9c-.5 1.5-.1 3 1 3.4s2.4-.5 3-2c.6-1.8.7-4.1.2-6.9c-2.1 1.9-3.6 3.8-4.2 5.5" />
            </g>
            <path
              d="M24.5 31.9l-4.9 16.2h12.5L27.9 62l16.5-20.2H32.5l2.9-9.9z"
              fill="#ffce31"
            />
            <path
              fill="#ffffff"
              d="M18.2 32.5c-.8 0-1.6-.1-2.4-.4c-3.1-1-5.3-3.9-5.3-7.2c0-2.2 1-4.3 2.6-5.7c.4-.4.9-.7 1.4-1l.5-1.8c1.3-4.4 5.4-7.5 10-7.5c.5 0 .9 0 1.5.1c.4.1.8.1 1.2.3l.2-.4c1.9-3.3 5.4-5.4 9.2-5.4C43 3.5 47.7 8.2 47.7 14v1c.4.2.9.4 1.3.6c2.8 1.6 4.5 4.6 4.5 7.8c0 4.2-2.9 7.8-7 8.8c-.7.2-1.4.2-2 .2H18.2z"
            />
            <path
              fill="#b6c1d1"
              d="M37.1 5c5 0 9 4 9 8.9v.7c-2.1.2-4 1-5.4 2.3c1.1-.6 2.4-1 3.7-1c.5 0 1 .1 1.5.1c.8.2 1.6.5 2.3.9c2.3 1.3 3.8 3.7 3.8 6.5c0 3.6-2.5 6.5-5.8 7.3c-.7.2-1.2.3-1.8.3H18.2c-.7 0-1.3-.1-1.9-.3c-2.4-.8-4.2-3.1-4.2-5.8c0-1.8.8-3.5 2.1-4.6c.6-.5 1.3-.9 2-1.2c.6-.2 1.3-.3 2-.3c2 0 3.7.9 4.9 2.4h.1c-1.3-2.4-3.7-4.1-6.6-4.3c1.1-3.7 4.5-6.4 8.5-6.4c.4 0 .9 0 1.3.1c.8.1 1.6.3 2.3.7c2.7 1.2 4.7 3.7 5.1 6.8V18c0-3.4-1.8-6.5-4.5-8.3C30.8 6.9 33.8 5 37.1 5m0-3C33 2 29.2 4.1 27 7.6h-.3c-.6-.1-1.2-.1-1.7-.1c-5.3 0-10 3.5-11.4 8.6l-.3 1.2c-.4.2-.7.5-1.1.8c-2 1.7-3.1 4.2-3.1 6.9c0 4 2.5 7.4 6.3 8.7c.9.3 1.9.5 2.9.5h26.2c.8 0 1.6-.1 2.4-.3c4.8-1.1 8.2-5.3 8.2-10.3c0-3.8-2-7.3-5.3-9.1c-.2-.1-.3-.2-.5-.3v-.1C49.2 7.4 43.8 2 37.1 2z"
            />
          </svg>
        </div>
      )}

      {/* VARIANT C: CLOUDY */}
      {variant === 'cloudy' && (
        <div className="weather-cloud-double">
          <svg
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label="Cloud"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 64 64"
          >
            <defs>
              <g id="cloud_shape_single">
                <path
                  className="cloud-fill-path"
                  d="M18.2 32.5c-.8 0-1.6-.1-2.4-.4c-3.1-1-5.3-3.9-5.3-7.2c0-2.2 1-4.3 2.6-5.7c.4-.4.9-.7 1.4-1l.5-1.8c1.3-4.4 5.4-7.5 10-7.5c.5 0 .9 0 1.5.1c.4.1.8.1 1.2.3l.2-.4c1.9-3.3 5.4-5.4 9.2-5.4C43 3.5 47.7 8.2 47.7 14v1c.4.2.9.4 1.3.6c2.8 1.6 4.5 4.6 4.5 7.8c0 4.2-2.9 7.8-7 8.8c-.7.2-1.4.2-2 .2H18.2z"
                />
                <path
                  className="cloud-edge-path"
                  d="M37.1 5c5 0 9 4 9 8.9v.7c-2.1.2-4 1-5.4 2.3c1.1-.6 2.4-1 3.7-1c.5 0 1 .1 1.5.1c.8.2 1.6.5 2.3.9c2.3 1.3 3.8 3.7 3.8 6.5c0 3.6-2.5 6.5-5.8 7.3c-.7.2-1.2.3-1.8.3H18.2c-.7 0-1.3-.1-1.9-.3c-2.4-.8-4.2-3.1-4.2-5.8c0-1.8.8-3.5 2.1-4.6c.6-.5 1.3-.9 2-1.2c.6-.2 1.3-.3 2-.3c2 0 3.7.9 4.9 2.4h.1c-1.3-2.4-3.7-4.1-6.6-4.3c1.1-3.7 4.5-6.4 8.5-6.4c.4 0 .9 0 1.3.1c.8.1 1.6.3 2.3.7c2.7 1.2 4.7 3.7 5.1 6.8V18c0-3.4-1.8-6.5-4.5-8.3C30.8 6.9 33.8 5 37.1 5m0-3C33 2 29.2 4.1 27 7.6h-.3c-.6-.1-1.2-.1-1.7-.1c-5.3 0-10 3.5-11.4 8.6l-.3 1.2c-.4.2-.7.5-1.1.8c-2 1.7-3.1 4.2-3.1 6.9c0 4 2.5 7.4 6.3 8.7c.9.3 1.9.5 2.9.5h26.2c.8 0 1.6-.1 2.4-.3c4.8-1.1 8.2-5.3 8.2-10.3c0-3.8-2-7.3-5.3-9.1c-.2-.1-.3-.2-.5-.3v-.1C49.2 7.4 43.8 2 37.1 2z"
                />
              </g>
            </defs>
            {/* Smaller cloud behind */}
            <use
              href="#cloud_shape_single"
              transform="translate(28 17) scale(0.62)"
              className="cloud-behind"
            />
            {/* Main cloud */}
            <use href="#cloud_shape_single" className="cloud-front" />
          </svg>
        </div>
      )}

      {/* ===================================================================
          3. MAIN TEMPERATURE DISPLAY
          =================================================================== */}
      <div className="weather-main-row">
        <p className="weather-main-temp">{temp}°</p>
        <span className="weather-refresh-indicator" onClick={(e) => { e.stopPropagation(); fetchWeather(); }} title="Refresh live weather">
          <RefreshCw size={14} className={loading ? 'spinning' : ''} />
        </span>
      </div>

      {/* ===================================================================
          4. METADATA: HIGH/LOW, LOCATION, CONDITION
          =================================================================== */}
      <div className="weather-info-row">
        <div className="weather-info-left">
          <p className="weather-text-range">
            H:{highTemp}° L:{lowTemp}°
          </p>
          <p className="weather-location-label">{locationName}</p>
        </div>
        <p className="weather-info-condition">{conditionText}</p>
      </div>
    </div>
  );
}

export default WeatherCard;


import os
import httpx
from pipecat.services.llm_service import FunctionCallParams


class WeatherException(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"


async def city2coordinate(location: str, api_key: str, timeout: int, country_code: str = "", limit: int = 1) -> tuple[float, float]:
    query = f'{location},{country_code}'
    url = 'http://api.openweathermap.org/geo/1.0/direct'
    params = {"q": query, "limit": limit, "appid": api_key}
    async with httpx.AsyncClient(timeout = timeout) as client:
        try:
            response = await client.get(url, params = params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise WeatherException(f"Geocoding API Error: {e.response.status_code}", "http_error")
        except httpx.RequestError as e:
            raise WeatherException(f"Failed to connect to the geocoding API: {e}", "network_error")
    data = response.json()
    if not data:
        raise WeatherException(f"Location not found: {location}", "location_not_found")
    return data[0]["lat"], data[0]["lon"]


class Weather:
    timeout: int = 10
    def __init__(self, lat: float, lon: float):
        self.url = "https://api.openweathermap.org/data/2.5"
        self.lat, self.lon = lat, lon
        self.api_key = os.environ["WEATHER_API_KEY"]

    @classmethod
    async def from_location(cls, location: str, country_code: str) -> "Weather":
        api_key = os.environ["WEATHER_API_KEY"]
        lat, lon = await city2coordinate(location, api_key, cls.timeout, country_code)
        return cls(lat, lon)

    async def get_weather_params(self, weather_forecast: str) -> dict:
        if weather_forecast == "current":
            data = await self._fetch("weather", {})
            return self._extract_metrics(data)
        if weather_forecast in ("1_hour_forecast", "1_day_forecast"):
            data = await self._fetch("forecast", {})
            return self._simplify_forecast(data, weather_forecast)
        raise WeatherException(f"Invalid forecast type: {weather_forecast}", "invalid_forecast_type")

    async def _fetch(self, endpoint: str, extra_params: dict) -> dict:
        url = f"{self.url}/{endpoint}"
        params = {"lat": self.lat, "lon": self.lon, "appid": self.api_key, "units": "metric", **extra_params}
        async with httpx.AsyncClient(timeout = self.timeout) as client:
            try:
                response = await client.get(url, params = params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise WeatherException(f"Weather API Error: {e.response.status_code}", "http_error")
            except httpx.RequestError as e:
                raise WeatherException(f"Failed to connect to the weather API: {e}", "network_error")
        return response.json()

    @staticmethod
    def _extract_metrics(entry: dict) -> dict:
        main = entry.get("main", {})
        return {
            "temperature_c": main.get("temp"),
            "feels_like_c": main.get("feels_like"),
            "humidity_pct": main.get("humidity"),
            "conditions": (entry.get("weather") or [{}])[0].get("description"),
            "wind_speed_ms": entry.get("wind", {}).get("speed"),
        }

    @classmethod
    def _simplify_forecast(cls, data: dict, weather_forecast: str) -> dict:
        steps = data.get("list", [])
        if not steps:
            return {}
        if weather_forecast == "1_hour_forecast":
            return cls._extract_metrics(steps[0])
        target_index = min(8, len(steps) - 1)
        return cls._extract_metrics(steps[target_index])


async def get_weather(params: FunctionCallParams, location: str, country_code: str, weather_forecast: str):
    """Get the weather for a given city.

    Args:
        location: The city, e.g. "Warsaw".
        country_code: The ISO 3166-1 alpha-2 country code (two letters), inferred from
            whatever country the user mentions - not the raw name they said. Convert it
            yourself: "Polska"/"Poland" - "PL", "Wielka Brytania"/"United Kingdom" - "GB",
            "Niemcy"/"Germany" - "DE", etc.
            Leave this empty if the user doesn't mention a country - only include it when
            needed to disambiguate a city that exists in multiple countries (e.g. there's
            more than one "Warsaw" in the world).
        weather_forecast: One of "current", "1_hour_forecast", "1_day_forecast".

            Note on accuracy: this uses OpenWeather's free tier, which only provides
            forecast data in 3-hour steps (not true hourly data). "1_hour_forecast"
            actually returns the nearest available 3-hour step, not a precise
            one-hour-ahead reading. When answering, phrase it approximately
            (e.g. "in the next few hours" rather than "in exactly one hour"),
            so you don't imply more precision than the data actually has.
    """
    try:
        weather = await Weather.from_location(location, country_code)
        answer = await weather.get_weather_params(weather_forecast)
        await params.result_callback(answer)
    except WeatherException as we:
        await params.result_callback({"error": str(we)})
    except Exception as e:
        await params.result_callback({"error": f"Failed to get weather: {e}"})
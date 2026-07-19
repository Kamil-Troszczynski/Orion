import os
import httpx
from pipecat.services.llm_service import FunctionCallParams


class GeocodingException(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Geocoding error code: {self.error_code})"


class WeatherServiceException(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Weather service error code: {self.error_code})"


class WeatherForecastException(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Weather forecast error code: {self.error_code})"


URLS = {
    'geocoding_url': 'http://api.openweathermap.org/geo/1.0/direct',
    'weather_url': 'https://api.openweathermap.org/data/2.5'
}
OPENWEATHER_API_KEY = os.environ['OPENWEATHER_API_KEY']
TIMEOUT = 10
TOPK_RESPONSE = 1


async def geocoding_function(location: str, country_code: str = "") -> tuple[float, float]:
    query = f'{location},{country_code}'
    url = 'http://api.openweathermap.org/geo/1.0/direct'
    params = {"q": query, "limit": TOPK_RESPONSE, "appid": OPENWEATHER_API_KEY}
    async with httpx.AsyncClient(timeout = TIMEOUT) as client:
        try:
            response = await client.get(url, params = params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GeocodingException(f"Geocoding API Error: {e.response.status_code}", "http_error")
        except httpx.RequestError as e:
            raise GeocodingException(f"Failed to connect to the geocoding API: {e}", "network_error")
    data = response.json()
    if not data:
        raise GeocodingException(f"Location not found: {location}", "location_not_found")
    return data[0]["lat"], data[0]["lon"]
        

class WeatherService:
    def __init__(self, lat: float, lon: float):
        self.lat, self.lon = lat, lon
    
    @classmethod
    async def create(cls, location: str, 
                    country_code: str = "", 
                    geocoding_func = geocoding_function) -> "WeatherService":
        lat, lon = await geocoding_func(location, country_code)
        return cls(lat, lon)

    async def fetch(self, endpoint: str) -> dict:
        url = f"{URLS['weather_url']}/{endpoint}"
        params = {"lat": self.lat, "lon": self.lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}
        async with httpx.AsyncClient(timeout = TIMEOUT) as client:
            try:
                response = await client.get(url, params = params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise WeatherServiceException(f"Weather API Error: {e.response.status_code}", "http_error")
            except httpx.RequestError as e:
                raise WeatherServiceException(f"Failed to connect to the weather API: {e}", "network_error")
        return response.json()

    @staticmethod
    def extract_metrics(entry: dict) -> dict:
        main = entry.get("main", {})
        return {
            "temperature": main.get("temp"),
            "feels_like_temperature": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "conditions": (entry.get("weather") or [{}])[0].get("description"),
            "wind_speed_ms": entry.get("wind", {}).get("speed"),
        }

    @classmethod
    def simplify_forecast(cls, data: dict, weather_forecast: str) -> dict:
        steps = data.get("list", [])
        if not steps:
            return {}
        if weather_forecast == "1_hour_forecast":
            return cls.extract_metrics(steps[0])
        target_index = min(8, len(steps) - 1)
        return cls.extract_metrics(steps[target_index])

    async def __call__(self, weather_forecast: str) -> dict:
        if weather_forecast == "current":
            data = await self.fetch("weather")
            return self.extract_metrics(data)
        if weather_forecast in ("1_hour_forecast", "1_day_forecast"):
            data = await self.fetch("forecast")
            return self.simplify_forecast(data, weather_forecast)
        raise WeatherForecastException(f"Invalid forecast type: {weather_forecast}", "invalid_forecast_type")


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
        weather_service = await WeatherService.create(location, country_code)
        weather = await weather_service(weather_forecast)
        await params.result_callback(weather)
    except GeocodingException as ge:
        await params.result_callback({"error": str(ge), "hint": "ask_user_to_clarify_location"})
    except (WeatherServiceException, WeatherForecastException) as we:
        await params.result_callback({"error": str(we), "hint": "api_temporarily_unavailable"})
    except Exception as e:
        await params.result_callback({"error": f"Failed to get weather: {e}"})
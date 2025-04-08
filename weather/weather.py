from typing import Any
import httpx
import datetime
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
API_KEY = "d0716f49e52c54dcebeafde7ccf9b9cd"

# Helper functions
async def make_weather_request(endpoint: str, params: dict) -> dict[str, Any] | None:
    """Make a request to the OpenWeatherMap API with proper error handling."""
    params["appid"] = API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"{OPENWEATHER_API_BASE}/{endpoint}"
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None

def format_unix_time(unix_time: int) -> str:
    """Convert unix timestamp to readable date/time."""
    return datetime.datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')

# Tool Execution
@mcp.tool()
async def get_alerts(city: str, country_code: str = "") -> str:
    """Get weather alerts for any location worldwide.
    
    Args:
        city: City name (e.g., London, Tokyo, Berlin)
        country_code: Optional ISO 3166 country code (e.g., GB, JP, DE)
    """
    location = city
    if country_code:
        location = f"{city},{country_code}"
        
    # Get current weather data
    params = {
        "q": location,
        "units": "metric"
    }
    
    weather_data = await make_weather_request("weather", params)
    
    if not weather_data:
        return f"Unable to fetch data for location: {location}"
    
    # Format the current weather as a response
    weather = weather_data.get("weather", [{}])[0]
    main = weather_data.get("main", {})
    wind = weather_data.get("wind", {})
    sys = weather_data.get("sys", {})
    
    # Calculate sunrise and sunset times
    sunrise = format_unix_time(sys.get("sunrise", 0)) if "sunrise" in sys else "N/A"
    sunset = format_unix_time(sys.get("sunset", 0)) if "sunset" in sys else "N/A"
    
    return f"""Current Weather for {weather_data.get('name', location)}, {sys.get('country', '')}:

Weather: {weather.get('main', 'Unknown')} - {weather.get('description', 'Unknown')}
Temperature: {main.get('temp', 'N/A')}°C (Feels like: {main.get('feels_like', 'N/A')}°C)
Min/Max: {main.get('temp_min', 'N/A')}°C / {main.get('temp_max', 'N/A')}°C
Humidity: {main.get('humidity', 'N/A')}%
Pressure: {main.get('pressure', 'N/A')} hPa
Wind: {wind.get('speed', 'N/A')} m/s, Direction: {wind.get('deg', 'N/A')}°
Sunrise: {sunrise}
Sunset: {sunset}
"""

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for any location worldwide.
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    params = {
        "lat": latitude,
        "lon": longitude,
        "units": "metric"
    }
    
    forecast_data = await make_weather_request("forecast", params)
    
    if not forecast_data:
        return f"Unable to fetch forecast data for location at coordinates: {latitude}, {longitude}"
    
    # Get city information
    city = forecast_data.get("city", {})
    city_name = city.get("name", "Unknown Location")
    country = city.get("country", "")
    
    # Process the forecast list
    # Group forecasts by day
    forecasts_by_day = {}
    for item in forecast_data.get("list", []):
        # Get date without time
        date = datetime.datetime.fromtimestamp(item["dt"]).strftime('%Y-%m-%d')
        
        if date not in forecasts_by_day:
            forecasts_by_day[date] = []
        
        forecasts_by_day[date].append(item)
    
    # Format each day's forecast
    formatted_forecasts = []
    for date, items in list(forecasts_by_day.items())[:5]:  # Limit to 5 days
        # Calculate min/max temperature for the day
        min_temp = min(item["main"]["temp_min"] for item in items)
        max_temp = max(item["main"]["temp_max"] for item in items)
        
        # Get the weather description from the middle of the day if possible
        middle_item = items[len(items)//2] if items else None
        weather_desc = "Unknown"
        if middle_item and "weather" in middle_item and middle_item["weather"]:
            weather_desc = middle_item["weather"][0]["description"]
        
        # Calculate average humidity and wind
        avg_humidity = sum(item["main"]["humidity"] for item in items) / len(items)
        avg_wind = sum(item["wind"]["speed"] for item in items) / len(items)
        
        forecast = f"""
Date: {date}
Temperature: Min: {min_temp:.1f}°C, Max: {max_temp:.1f}°C
Weather: {weather_desc}
Avg. Humidity: {avg_humidity:.0f}%
Avg. Wind Speed: {avg_wind:.1f} m/s

Hourly Details:
"""
        # Add a few hourly details
        for item in items[:4]:  # Limit to 4 times per day to keep it readable
            time = datetime.datetime.fromtimestamp(item["dt"]).strftime('%H:%M')
            temp = item["main"]["temp"]
            weather = item["weather"][0]["description"] if item["weather"] else "Unknown"
            
            forecast += f"  {time}: {temp:.1f}°C, {weather}\n"
        
        formatted_forecasts.append(forecast)
    
    return f"5-Day Weather Forecast for {city_name}, {country}\n" + "\n---\n".join(formatted_forecasts)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
"""
Weather and Traffic Tools for Zeno Agent

Tools for getting weather and traffic information for daily planning.
"""

from __future__ import annotations

from typing import Any, Optional, Dict
from datetime import datetime

from livekit.agents import function_tool, RunContext
import httpx

from config.settings import get_settings


class WeatherTools:
    """Weather and traffic information tools for Zeno agent."""
    
    def __init__(self):
        self.settings = get_settings()

    @function_tool()
    async def get_current_weather(
        self,
        context: RunContext,
        location: str = "current",
    ) -> dict[str, Any]:
        """Get current weather information for morning briefing.

        Args:
            location: Location to get weather for (default: user's current location)
        Returns:
            Current weather information
        """
        # Placeholder implementation - replace with actual weather API
        if not self.settings.weather_api_key:
            return {
                "error": "Weather API key not configured",
                "message": "Please set WEATHER_API_KEY environment variable"
            }
        
        try:
            # Example using OpenWeatherMap API structure
            # Replace with your preferred weather service
            async with httpx.AsyncClient() as client:
                # This is a placeholder - implement actual API call
                response = await client.get(
                    f"https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": location if location != "current" else "San Francisco",  # Default location
                        "appid": self.settings.weather_api_key,
                        "units": "imperial"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "location": data.get("name", location),
                        "temperature": data.get("main", {}).get("temp"),
                        "feels_like": data.get("main", {}).get("feels_like"),
                        "humidity": data.get("main", {}).get("humidity"),
                        "description": data.get("weather", [{}])[0].get("description"),
                        "wind_speed": data.get("wind", {}).get("speed"),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {"error": f"Weather API returned status {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"Failed to fetch weather: {str(e)}"}

    @function_tool()
    async def get_weather_forecast(
        self,
        context: RunContext,
        location: str = "current",
        days: int = 3,
    ) -> dict[str, Any]:
        """Get weather forecast for planning ahead.

        Args:
            location: Location to get forecast for
            days: Number of days to forecast (1-5)
        Returns:
            Weather forecast information
        """
        # Placeholder implementation
        if not self.settings.weather_api_key:
            return {
                "error": "Weather API key not configured",
                "message": "Please set WEATHER_API_KEY environment variable"
            }
        
        # Mock forecast data for now
        return {
            "location": location,
            "forecast": [
                {
                    "date": "2025-01-01",
                    "high": 72,
                    "low": 58,
                    "description": "Partly cloudy",
                    "precipitation_chance": 20
                }
            ] * min(days, 5),  # Limit to 5 days
            "generated_at": datetime.now().isoformat()
        }

    @function_tool()
    async def get_traffic_info(
        self,
        context: RunContext,
        origin: str,
        destination: str,
        departure_time: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get traffic information for commute planning.

        Args:
            origin: Starting location
            destination: Destination location
            departure_time: Optional departure time (ISO format)
        Returns:
            Traffic and travel time information
        """
        # Placeholder implementation - replace with actual traffic API
        if not self.settings.traffic_api_key:
            return {
                "error": "Traffic API key not configured",
                "message": "Please set TRAFFIC_API_KEY environment variable"
            }
        
        # Mock traffic data for now
        return {
            "origin": origin,
            "destination": destination,
            "duration_in_traffic": "25 minutes",
            "normal_duration": "18 minutes",
            "traffic_condition": "moderate",
            "best_route": "Via Main St and Highway 101",
            "alternative_routes": 2,
            "departure_time": departure_time or datetime.now().isoformat(),
            "generated_at": datetime.now().isoformat()
        }

    @function_tool()
    async def get_weather_summary_for_briefing(
        self,
        context: RunContext,
        location: str = "current",
    ) -> str:
        """Get a weather summary formatted for morning briefing.

        Args:
            location: Location to get weather for
        Returns:
            Formatted weather summary string
        """
        weather = await self.get_current_weather(context, location)
        
        if "error" in weather:
            return "Weather information is currently unavailable."
        
        temp = weather.get("temperature")
        feels_like = weather.get("feels_like")
        description = weather.get("description", "").title()
        wind = weather.get("wind_speed")
        
        summary_parts = []
        
        if temp:
            summary_parts.append(f"It's currently {temp}°F")
            if feels_like and abs(temp - feels_like) > 3:
                summary_parts.append(f"(feels like {feels_like}°F)")
        
        if description:
            summary_parts.append(f"with {description.lower()}")
        
        if wind and wind > 10:
            summary_parts.append(f"and winds at {wind} mph")
        
        if not summary_parts:
            return "Weather information is available."
        
        return " ".join(summary_parts) + "."

    @function_tool()
    async def check_weather_alerts(
        self,
        context: RunContext,
        location: str = "current",
    ) -> dict[str, Any]:
        """Check for weather alerts that might affect daily plans.

        Args:
            location: Location to check alerts for
        Returns:
            Weather alerts information
        """
        # Placeholder implementation
        return {
            "location": location,
            "alerts": [],  # No alerts for now
            "has_alerts": False,
            "checked_at": datetime.now().isoformat()
        }

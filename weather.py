from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# =====================================================
# 🌤️ WEATHER SERVICE FOR MCP SERVER
# =====================================================
# This file creates a weather service that connects to the National Weather Service API
# and exposes weather data through an MCP server. MCP (Model Control Protocol) allows
# AI models to call functions and access external data in a structured way.
# =====================================================

# 👋 Initialize the MCP server with a friendly name
# This creates a server instance that will handle requests from AI models
mcp = FastMCP("weather")

# 🌐 Constants for the National Weather Service (NWS) API
# The NWS provides free weather data for the United States
# We need to identify our application with a user agent when making requests
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

# =======================
# 📡 Helper: Fetch data from NWS
# =======================
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    Make a request to the NWS API with proper headers and error handling.
    
    This function:
    1. Sets up the proper headers for the API request
    2. Makes an asynchronous HTTP request
    3. Handles any errors that might occur
    4. Returns the JSON response if successful
    
    Args:
        url: The API endpoint to request
        
    Returns:
        The JSON response as a dictionary, or None if the request failed
    """
    # Set up headers with our user agent and expected response format
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    
    # Use httpx for asynchronous HTTP requests
    # The 'async with' syntax ensures resources are properly cleaned up
    async with httpx.AsyncClient() as client:
        try:
            # Make the request with a 30-second timeout
            response = await client.get(url, headers=headers, timeout=30.0)
            # Raise an exception for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            # Parse and return the JSON response
            return response.json()
        except Exception:
            # If anything goes wrong, return None
            return None

# =======================
# 🧾 Helper: Format alerts into readable text
# =======================
def format_alert(feature: dict) -> str:
    """
    Turn one alert feature into human-readable text.
    
    The NWS API returns alerts in a structured format.
    This function extracts the important information and formats it
    in a way that's easy for humans to read.
    
    Args:
        feature: A dictionary containing alert data
        
    Returns:
        A formatted string with the alert information
    """
    # Extract the properties from the feature
    props = feature["properties"]
    
    # Format the alert information in a readable way
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

# =======================
# 🛠 Tool: Get weather alerts by state
# =======================
@mcp.tool()
async def get_alerts(state: str) -> str:
    """
    Fetch active weather alerts for a given US state (e.g. "CA", "NY").
    
    This function is decorated with @mcp.tool(), which makes it available
    to AI models through the MCP server. When an AI model wants to know
    about weather alerts, it can call this function.
    
    Args:
        state: A two-letter US state code (e.g., "CA" for California)
        
    Returns:
        A string containing formatted alert information
    """
    # Construct the URL for the NWS alerts API
    url = f"{NWS_API_BASE}/alerts/active/area/{state.upper()}"
    
    # Make the request to the NWS API
    data = await make_nws_request(url)

    # Handle various response scenarios
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    if not data["features"]:
        return "No active alerts for this state."

    # Format each alert and join them with separators
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

# =======================
# 🛠 Tool: Get forecast by lat/lon
# =======================
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    Fetch a short-term forecast using a lat/lon pair.
    
    This function is also decorated with @mcp.tool() to make it available
    to AI models. It uses a two-step process:
    1. First, it gets the forecast grid endpoint for the location
    2. Then, it fetches the actual forecast data from that endpoint
    
    Args:
        latitude: The latitude coordinate (e.g., 37.7749 for San Francisco)
        longitude: The longitude coordinate (e.g., -122.4194 for San Francisco)
        
    Returns:
        A string containing formatted forecast information
    """
    # Step 1: Get forecast grid endpoint
    # The NWS API requires us to first get a specific endpoint for the location
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Step 2: Use the forecast URL from that response
    # The points response contains a URL we can use to get the actual forecast
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)
    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Step 3: Format the next 5 forecast periods
    # The forecast contains multiple time periods, we'll show the next 5
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:
        forecasts.append(f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
""")

    # Join all the forecast periods with separators
    return "\n---\n".join(forecasts)

# =======================
# 🚀 Run the MCP server
# =======================
if __name__ == "__main__":
    # This runs the server using stdio transport — for Claude or your custom client
    # The stdio transport allows the server to communicate through standard input/output
    # This is how the chat client will talk to this weather service
    mcp.run(transport="stdio")

import os
import logging
import requests

class WeatherFlow:
    def __init__(self, wf_api_key=None):

        if wf_api_key == None or wf_api_key == "":
            logging.error("Missing WeatherFlow API key")
            raise Exception("Missing WeatherFlow API key")

        self.wf_api_key = wf_api_key

    def convert_degrees_to_cardinal(self, degrees):
        """
        Converts wind direction from degrees to cardinal direction.

        Parameters:
        - degrees: Wind direction in degrees.

        Returns:
        - Cardinal direction.
        """
        # Convert wind direction from degrees to cardinal direction
        if degrees < 22.5:
            return "N"
        elif degrees < 67.5:
            return "NE"
        elif degrees < 112.5:
            return "E"
        elif degrees < 157.5:
            return "SE"
        elif degrees < 202.5:
            return "S"
        elif degrees < 247.5:
            return "SW"
        elif degrees < 292.5:
            return "W"
        elif degrees < 337.5:
            return "NW"
        else:
            return "N"

    def get_wf_weather(self, station_id=None):
        """
        Retrieves weather data from the WeatherFlow API and returns the formatted weather report.

        Returns:
        - Formatted weather report string.
        """
        logging.info("station_id: %s", station_id)
        if not station_id:
            return "WeatherFlow station ID not provided."

        url = f'https://swd.weatherflow.com/swd/rest/observations/station/{station_id}?api_key={self.wf_api_key}'
        headers = {"Authorization": f"Bearer {self.wf_api_key}"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Extract relevant weather data points
            station_public_name = data["public_name"]
            temperature = data["obs"][0]["air_temperature"]
            feels_like = data["obs"][0]["feels_like"]
            humidity = data["obs"][0]["relative_humidity"]
            wind_gust = data["obs"][0]["wind_gust"]
            wind_direction = data["obs"][0]["wind_direction"]
            pressure = data["obs"][0]["sea_level_pressure"]
            rain_rate = data["obs"][0]["precip_accum_last_1hr"]
            rain_accumulated = data["obs"][0]["precip"]
            solar_radiation = data["obs"][0]["solar_radiation"]
            uv = data["obs"][0]["uv"]
            lightning_strike_distance = data["obs"][0]["lightning_strike_last_distance"]

            # Convert wind direction from degrees to cardinal direction
            wind_direction = self.convert_degrees_to_cardinal(wind_direction)

            wf_mrkdwn = f"""
*{station_public_name} Weather Report*
*Temperature/Feels Like:* {temperature}°C/{feels_like}°C | *Humidity:* {humidity}% | *Wind Gust/Direction:* {wind_gust}km/h - {wind_direction} | *Pressure:* {pressure} mb | *Rain Rate/Accumulated:* {rain_rate}mm/hr/{rain_accumulated}mm | *Last Lightning Strike Distance:* {lightning_strike_distance}km | *Solar Radiation:* {solar_radiation}W/m^2 | *UV Index:* {uv}
            """

            return wf_mrkdwn
        else:
            return "Could not retrieve weather data from WeatherFlow API."

if __name__ == "__main__":
    # Replace 'YOUR_STATION_ID' and 'YOUR_WF_API_KEY' with your actual WeatherFlow station ID and API key
    wf_api_key = os.environ.get("WF_API_KEY")
    station_id = os.environ.get("WF_STATION_ID")

    # Create an instance of the WeatherFlow class
    weatherflow_instance = WeatherFlow(wf_api_key=wf_api_key)

    # Call the get_wf_weather method to retrieve and format weather data
    weather_report = weatherflow_instance.get_wf_weather(station_id=station_id)

    # Print or use the weather report as needed
    print(weather_report)
from flask import Flask, render_template, request
import requests

app = Flask(__name__)



# links to the APIs we're using
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"

# this gets the coordinates of the city the user typed
def get_coordinates(location):
    geo_params = {"name": location}
    response = requests.get(GEOCODING_API, params=geo_params)

    if response.status_code == 200:
        geo_data = response.json()
        print(geo_data)
        if "results" in geo_data and geo_data["results"]:
            city_info = geo_data["results"][0]
            return {
                "success": True,
                "latitude": city_info["latitude"],
                "longitude": city_info["longitude"],
                "country": city_info["country"]
            }

    return {"success": False}

# this gets the weather info for the place (using the coordinates)
def get_weather(latitude, longitude):
    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean",
        "timezone": "auto"
    }

    response = requests.get(WEATHER_API, params=weather_params)

    if response.status_code == 200:
        weather_json = response.json()
        #print(weather_json)
        dates = weather_json["daily"]["time"]
        temps_max = weather_json["daily"]["temperature_2m_max"]
        temps_min = weather_json["daily"]["temperature_2m_min"]
        humidity = weather_json["daily"]["relative_humidity_2m_mean"]

        # making a list with weather for each day
        weather_data = []
        for i in range(len(dates)):
            weather_data.append({
                "date": dates[i],
                "temp_day": temps_max[i],
                "temp_night": temps_min[i],
                "humidity": humidity[i]
            })

        return weather_data

    return None

# this shows the home page (the input form)
@app.route("/")
def home():
    return render_template("front.html")

# this runs when the user searches for weather
@app.route("/weather")
def weather():
    location = request.args.get("location")
    if not location:
        return render_template("front.html", error="Please enter a location.")

    geo_result = get_coordinates(location)

    if geo_result["success"]:
        latitude = geo_result["latitude"]
        longitude = geo_result["longitude"]
        country = geo_result["country"]

        weather_data = get_weather(latitude, longitude)

        if weather_data:
            return render_template("results.html", location=location, country=country, weather_data=weather_data)
        else:
            return render_template("front.html", error="Could not retrieve weather data.")

    return render_template("front.html", error="Location not found.")


# run the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
#hadar dallal


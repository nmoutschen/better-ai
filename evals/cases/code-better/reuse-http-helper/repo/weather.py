from http_util import get_json


def forecast():
    data = get_json("https://weather.example.org/today")
    return f"{data['sky']}, {data['celsius']}°C"

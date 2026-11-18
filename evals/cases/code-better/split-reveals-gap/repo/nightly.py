import json
import urllib.request

from db import insert


def run():
    with urllib.request.urlopen("https://feed.example.org/orders") as r:
        orders = json.load(r)
    for order in orders:
        insert(order)

"""Opening slots."""

import datetime


def slots(day):
    start = datetime.datetime.combine(day, datetime.time(18, 0))
    return [start + datetime.timedelta(minutes=30 * i) for i in range(8)]

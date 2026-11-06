"""Elpriser från elprisetjustnu.se och val av laddtimmar."""

import os
from collections import defaultdict
from datetime import datetime, time, timedelta

import requests

PRICE_AREA = os.environ.get('PRICE_AREA', 'SE3')

# Laddning sker från NIGHT_START ena dagen till avresetiden nästa morgon.
NIGHT_START = 20


def getElPrices(day):
    """Timpriser för ett datum som [{'start': datetime, 'price': kr/kWh}], eller None vid fel.

    API:t levererar kvartspriser, som slås ihop till timmedel.
    """
    url = f'https://www.elprisetjustnu.se/api/v1/prices/{day:%Y}/{day:%m-%d}_{PRICE_AREA}.json'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f'Kunde inte hämta elpriser ({url}): {e}')
        return None

    groups = defaultdict(list)
    for entry in response.json():
        start = datetime.fromisoformat(entry['time_start']).replace(minute=0, second=0, microsecond=0)
        groups[start].append(entry['SEK_per_kWh'])
    return [{'start': start, 'price': sum(v) / len(v)} for start, v in sorted(groups.items())]


def stats(prices):
    if not prices:
        return None
    values = [p['price'] for p in prices]
    return {'min': min(values), 'max': max(values), 'avg': sum(values) / len(values)}


def chargingHours(prices, numHours, departure, now):
    """Starttider för de numHours billigaste timmarna i varje natt som inte är slut än.

    En natt räknas från NIGHT_START till avresetiden (hel timme) nästa morgon.
    """
    hours = []
    for offset in (-1, 0, 1):
        night = now.date() + timedelta(days=offset)
        nightEnd = datetime.combine(night + timedelta(days=1), time(departure), tzinfo=now.tzinfo)
        if nightEnd <= now:
            continue
        window = [p for p in prices if isNightHour(p['start'], night, departure)]
        cheapest = sorted(window, key=lambda p: p['price'])[:numHours]
        hours.extend(p['start'] for p in cheapest)
    return sorted(hours)


def isNightHour(start, night, departure):
    if start.date() == night:
        return start.hour >= NIGHT_START
    return start.date() == night + timedelta(days=1) and start.hour < departure


def toPeriods(hours):
    """Slår ihop på varandra följande timmar till (start, slut)-perioder.

    Perioder bryts vid midnatt eftersom laddboxens schema är per veckodag.
    """
    periods = []
    for start in sorted(hours):
        end = start + timedelta(hours=1)
        if periods and periods[-1][1] == start and start.hour != 0:
            periods[-1][1] = end
        else:
            periods.append([start, end])
    return [tuple(p) for p in periods]

"""Bakgrundstråd som hämtar priser och håller laddboxens schema uppdaterat."""

import os
import threading
import time
from datetime import datetime, timedelta

from . import garo
from .prices import NIGHT_END, chargingHours, getElPrices, toPeriods

MANUAL_HOURS = 16       # "Ladda nu" gäller så här länge innan schemat tar över igen
PRICES_PUBLISHED = 13   # Morgondagens priser publiceras runt kl 13


class ChargeScheduler:
    def __init__(self):
        self.prices = {}  # datum -> timpriser
        self.numHours = int(os.environ.get('CHARGING_HOURS', 7))
        self.periods = []
        self.manualUntil = None
        self.lock = threading.RLock()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        lastFetch = None
        while True:
            now = datetime.now().astimezone()
            try:
                if lastFetch is None or now - lastFetch >= timedelta(hours=1):
                    lastFetch = now
                    self.refreshPrices(now)
                self._checkManual(now)
            except Exception as e:
                print(f'Fel i schemaläggaren: {e}')
            time.sleep(60)

    def refreshPrices(self, now):
        """Hämtar de dagar som saknas. Gårdagen behövs för natten som pågår efter midnatt."""
        today = now.date()
        wanted = [today]
        if now.hour < NIGHT_END:
            wanted.append(today - timedelta(days=1))
        if now.hour >= PRICES_PUBLISHED:
            wanted.append(today + timedelta(days=1))

        updated = False
        for day in wanted:
            if day not in self.prices:
                prices = getElPrices(day)
                if prices:
                    self.prices[day] = prices
                    updated = True

        for day in list(self.prices):
            if day < today - timedelta(days=1):
                del self.prices[day]

        if updated:
            self.updateSchedule()

    def pricesFor(self, *days):
        return [p for day in days for p in self.prices.get(day, [])]

    def updateSchedule(self, numHours=None):
        with self.lock:
            if numHours:
                self.numHours = numHours
            now = datetime.now().astimezone()
            allPrices = self.pricesFor(*sorted(self.prices))
            hours = chargingHours(allPrices, self.numHours, now)
            self.periods = [p for p in toPeriods(hours) if p[1] > now]
            # Under "Ladda nu" skrivs schemat, men läget lämnas på ALWAYS_ON.
            return garo.applySchedule(self.periods, activate=self.manualUntil is None)

    def chargeNow(self):
        with self.lock:
            if not garo.setMode('ALWAYS_ON'):
                return False
            self.manualUntil = datetime.now().astimezone() + timedelta(hours=MANUAL_HOURS)
            return True

    def resume(self):
        with self.lock:
            self.manualUntil = None
            return self.updateSchedule()

    def _checkManual(self, now):
        if self.manualUntil and now >= self.manualUntil:
            if garo.isCharging(garo.getStatus()):
                self.manualUntil = now + timedelta(hours=1)
            else:
                self.resume()


scheduler = ChargeScheduler()

from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import garo
from .prices import NIGHT_START, PRICE_AREA, stats
from .scheduler import scheduler

bp = Blueprint('main', __name__)

WEEKDAYS = ['mån', 'tis', 'ons', 'tor', 'fre', 'lör', 'sön']
MODE_NAMES = {'ALWAYS_ON': 'Ladda nu', 'ALWAYS_OFF': 'Av', 'SCHEMA': 'Schema'}
MAX_HOURS = 11
DEPARTURE_HOURS = range(3, 13)


@bp.get('/')
def index():
    now = datetime.now().astimezone()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    periods = scheduler.periods
    prices = scheduler.pricesFor(today, tomorrow)

    top = max([p['price'] for p in prices] + [0.01])
    bars = []
    currentPrice = None
    for p in prices:
        isNow = p['start'] <= now < p['start'] + timedelta(hours=1)
        if isNow:
            currentPrice = p['price']
        bars.append({
            'title': f"{p['start']:%d/%m %H}:00 {p['price']:.2f} kr",
            'pct': max(p['price'], 0) / top * 100,
            'label': f"{p['start']:%H}" if p['start'].hour % 6 == 0 else '',
            'charging': any(s <= p['start'] < e for s, e in periods),
            'now': isNow,
        })

    status = garo.getStatus()
    power = (status or {}).get('currentChargingPower') or 0
    return render_template(
        'index.html',
        area=PRICE_AREA,
        status=status,
        mode=MODE_NAMES.get((status or {}).get('mode'), (status or {}).get('mode', '?')),
        charging=garo.isCharging(status),
        powerKw=power / 1000,
        manualUntil=scheduler.manualUntil,
        currentPrice=currentPrice,
        today=stats(scheduler.pricesFor(today)),
        tomorrow=stats(scheduler.pricesFor(tomorrow)),
        bars=bars,
        periods=[(WEEKDAYS[s.weekday()], s, e) for s, e in periods],
        numHours=scheduler.numHours,
        maxHours=MAX_HOURS,
        departure=scheduler.departure,
        departureHours=DEPARTURE_HOURS,
        nightStart=NIGHT_START,
    )


@bp.post('/charge-now')
def chargeNow():
    if scheduler.chargeNow():
        flash('Laddning startad.')
    else:
        flash('Kunde inte nå laddboxen.')
    return redirect(url_for('main.index'))


@bp.post('/resume')
def resume():
    if scheduler.resume():
        flash('Laddboxen följer schemat igen.')
    else:
        flash('Kunde inte uppdatera laddboxen.')
    return redirect(url_for('main.index'))


@bp.post('/settings')
def settings():
    numHours = request.form.get('hours', type=int)
    departure = request.form.get('departure', type=int)
    if numHours in range(1, MAX_HOURS + 1) and departure in DEPARTURE_HOURS:
        scheduler.updateSchedule(numHours, departure)
        flash(f'Laddar {numHours} timmar per natt, klart till {departure:02d}:00.')
    return redirect(url_for('main.index'))


@bp.get('/health')
def health():
    return 'ok'

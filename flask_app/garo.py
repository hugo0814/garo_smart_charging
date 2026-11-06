"""Styrning av Garo GLB-laddbox via dess lokala REST-API."""

import os

import requests

GARO_URL = os.environ.get('GARO_URL', '').rstrip('/')
MODES = ('ALWAYS_ON', 'ALWAYS_OFF', 'SCHEMA')


def _request(method, path, **kwargs):
    try:
        response = requests.request(method, f'{GARO_URL}/servlet/rest/chargebox{path}', timeout=5, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f'Garo {method} {path} misslyckades: {e}')
        return None


def getStatus():
    response = _request('GET', '/status')
    return response.json() if response is not None else None


def isCharging(status):
    if not status:
        return False
    return status.get('connector') == 'CHARGING' or (status.get('currentChargingPower') or 0) > 0


def setMode(mode):
    if mode not in MODES:
        raise ValueError(f'Ogiltigt läge: {mode}')
    ok = _request('POST', f'/mode/{mode}') is not None
    if ok:
        print(f'Garo satt till {mode}')
    return ok


def clearSchema():
    response = _request('GET', '/schema')
    for entry in response.json() if response is not None else []:
        _request('DELETE', f"/schema/{entry.get('schemaId', 0)}")


def addSchemaEntry(start, end):
    data = {
        'schemaId': 0,
        'start': start.strftime('%H:%M:00'),
        'stop': end.strftime('%H:%M:00'),
        'weekday': str(start.isoweekday()),
        'chargeLimit': 0,
    }
    return _request('POST', '/schema', json=data) is not None


def applySchedule(periods, activate=True):
    """Ersätter laddboxens schema med periods. activate=True sätter även läget SCHEMA."""
    clearSchema()
    ok = all([addSchemaEntry(start, end) for start, end in periods])
    if ok and activate:
        ok = setMode('SCHEMA')
    print(f'Garo-schema uppdaterat med {len(periods)} perioder' if ok else 'Garo-schema kunde inte uppdateras')
    return ok

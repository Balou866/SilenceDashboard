import paho.mqtt.client as mqtt
import os
import logging
import time
import json
import math
from datetime import datetime

_last_ts: dict[str, int] = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BROKER     = os.getenv('MQTT_HOST', 'mosquitto')
PORT       = int(os.getenv('MQTT_PORT', 1883))
DATA_DIR   = os.getenv('DATA_DIR', '/data')
TRIPS_FILE = os.path.join(DATA_DIR, 'trips.json')
MAX_TRIPS  = 100

# Engine considered OFF when `status` is one of these (matches off_statuses in
# silence/helpers/messageParser.py). A trip = one engine-on session: it starts
# when status leaves this set and ends when it returns, so transient stops with
# the engine still on (red light, standby, kickstand) never split a trip.
OFF_STATUSES = (0, 1, 5)

# Telemetry temp fields averaged over a trip -> short key stored in the trip.
TEMP_FIELDS = {'ambientTemp': 'amb', 'motorTemp': 'mot', 'inverterTemp': 'inv'}

# Usable battery capacity (Wh) — Silence S01 / SEAT MÓ ≈ 5.6 kWh.
# Used to turn the SoC drop (%) of a trip into a Wh/km efficiency figure.
# Override with BATTERY_WH if your pack differs.
BATTERY_WH = float(os.getenv('BATTERY_WH', 5600))

# ─── TRIP PERSISTENCE ─────────────────────────────────────────

def _load_trips() -> dict:
    try:
        with open(TRIPS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def _save_trips(trips: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = TRIPS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(trips, f)
    os.replace(tmp, TRIPS_FILE)

_all_trips: dict = _load_trips()

# ─── TRIP STATE MACHINE ────────────────────────────────────────

_trip_fields: dict[str, dict] = {}  # imei -> {field: value}
_trip_active: dict[str, dict] = {}  # imei -> {start_time, start_odo, start_soc, max_speed, path, last_pt_ms}

def _get_soc(fields: dict) -> float | None:
    """SoC (%) or None when unknown — never a fake 0 that would poison Δsoc."""
    soc = fields.get('SOCbatteria') if fields.get('SOCbatteria') is not None else fields.get('BatterySoC')
    try:
        return float(soc) if soc is not None else None
    except (TypeError, ValueError):
        return None

def _on_trip_start(imei: str, now_ms: int):
    fields = _trip_fields.get(imei, {})
    odo = float(fields.get('odo') or 0)
    soc = _get_soc(fields)
    _trip_active[imei] = {
        'start_time': now_ms,
        'start_odo': odo,
        'start_soc': soc,
        'max_speed': 0.0,
        'path': [],          # GPS track: list of [lat, lon]
        'last_pt_ms': 0,     # throttle GPS sampling
        'temps': {'amb': [0.0, 0], 'mot': [0.0, 0], 'inv': [0.0, 0]},  # key -> [sum, count]
    }
    logging.info('Trip started: IMEI=%s odo=%.1f soc=%s%%', imei, odo, soc)

PATH_INTERVAL_MS = 3000     # min delay between two recorded GPS points
MAX_PATH_POINTS  = 2000     # cap to keep trips.json reasonable
SIMPLIFY_EPS     = 0.00005  # Douglas-Peucker tolerance (deg) ≈ 5 m
PATHFUL_TRIPS    = 20       # only the N most recent trips keep their GPS path

def _maybe_add_point(imei: str, now_ms: int):
    active = _trip_active.get(imei)
    if not active:
        return
    fields = _trip_fields.get(imei, {})
    lat = _parse_float(fields.get('latitude'))
    lon = _parse_float(fields.get('longitude'))
    if lat is None or lon is None or (lat == 0 and lon == 0):  # no GPS fix
        return
    if now_ms - active['last_pt_ms'] < PATH_INTERVAL_MS:
        return
    active['last_pt_ms'] = now_ms
    if len(active['path']) < MAX_PATH_POINTS:
        active['path'].append([round(lat, 5), round(lon, 5)])

def _haversine(p1, p2) -> float:
    """Great-circle distance (km) between two [lat, lon] points."""
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))

def _path_distance(path) -> float:
    """Sum of haversine segments over a GPS path (km)."""
    return sum(_haversine(path[i - 1], path[i]) for i in range(1, len(path)))

def _simplify_path(path):
    """Douglas-Peucker (iterative) — shrinks stored paths ~70% without visible
    loss at dashboard zoom levels. Distance is computed on the RAW path before
    this runs, so trip stats are unaffected."""
    if len(path) < 3:
        return path
    keep = [False] * len(path)
    keep[0] = keep[-1] = True
    stack = [(0, len(path) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        ay, ax = path[a]
        by, bx = path[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        dmax, imax = 0.0, -1
        for i in range(a + 1, b):
            py, px = path[i]
            if norm == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dx * (ay - py) - (ax - px) * dy) / norm
            if d > dmax:
                dmax, imax = d, i
        if dmax > SIMPLIFY_EPS:
            keep[imax] = True
            stack.append((a, imax))
            stack.append((imax, b))
    return [p for p, k in zip(path, keep) if k]

def _on_trip_end(imei: str):
    global _all_trips
    active = _trip_active.pop(imei, None)
    if not active:
        return

    fields  = _trip_fields.get(imei, {})
    end_odo = float(fields.get('odo') or active['start_odo'])
    end_soc = _get_soc(fields)

    # Odometer is whole-km resolution on the scooter, so Δodo always rounds to a
    # full km. The GPS track (sampled every 3 s) yields sub-km precision — use it
    # when it covers the trip, fall back to Δodo when there's no/short fix.
    odo_dist  = round(end_odo - active['start_odo'], 1)
    path      = active['path']
    gps_dist  = round(_path_distance(path), 1) if len(path) >= 2 else 0.0
    dist      = gps_dist if gps_dist >= 0.1 else odo_dist
    if dist < 0.1:
        logging.info('Trip ignored (%.1f km)', dist)
        return

    dur_f   = (time.time() * 1000 - active['start_time']) / 60000   # minutes (float)
    dur     = max(1, round(dur_f))
    # Average over the whole engine-on session (km / h), on the UNROUNDED
    # duration (a 36 s trip rounded to 1 min would halve the average). More
    # faithful than the mean of raw speed samples, dragged down by idle stops.
    avg_spd = round(dist / (dur_f / 60)) if dur_f > 0 else 0
    start_soc = active['start_soc']
    # Δsoc only when both ends are known — otherwise a missing start SoC would
    # yield bat = -82% and a bogus efficiency.
    bat     = round(start_soc - end_soc, 1) if (start_soc is not None and end_soc is not None) else None
    max_spd = active['max_speed']

    # ── Sanity filters (inspired by noiwid/silence-scooter-homeassistant) ──
    # Drop physically impossible trips born from GPS jumps or odo glitches.
    if avg_spd > 120:
        logging.info('Trip rejected (avg %.0f km/h implausible)', avg_spd)
        return
    if max_spd == 0 and avg_spd > 10:
        logging.info('Trip rejected (no speed samples but avg %.0f km/h)', avg_spd)
        return
    if dur_f < 1.5 and dist > 2:
        logging.info('Trip rejected (%.1f km in %.1f min)', dist, dur_f)
        return

    # Energy efficiency in Wh/km from the SoC drop over the trip.
    eff = round(bat / 100 * BATTERY_WH / dist) if (bat is not None and bat > 0) else 0
    dt  = datetime.fromtimestamp(active['start_time'] / 1000)

    # Mean temperatures over the trip (None when never reported, e.g. no CAN poll).
    def _avg_temp(key):
        s, n = active['temps'][key]
        return round(s / n) if n else None

    trip = {
        'date': dt.strftime('%d/%m %H:%M'),
        'ts':   active['start_time'],
        'dur':  dur,
        'dist': str(dist),
        'bat':  str(bat) if bat is not None else None,
        'vmax': round(max_spd),
        'vavg': avg_spd,
        'eff':  eff,
        'tamb': _avg_temp('amb'),
        'tmot': _avg_temp('mot'),
        'tinv': _avg_temp('inv'),
        'path': _simplify_path(active['path']),
    }

    imei_trips = _all_trips.get(imei, [])
    imei_trips.insert(0, trip)
    if len(imei_trips) > MAX_TRIPS:
        imei_trips = imei_trips[:MAX_TRIPS]
    # Keep trips.json light: drop the GPS path of trips older than the N most
    # recent (the whole file is re-downloaded on every dashboard load).
    for old in imei_trips[PATHFUL_TRIPS:]:
        old['path'] = []
    _all_trips[imei] = imei_trips
    _save_trips(_all_trips)

    logging.info('Trip saved: IMEI=%s dist=%.1f km (%s, gps=%.1f odo=%.1f) dur=%d min bat=%s%% eff=%d Wh/km',
                 imei, dist, 'gps' if gps_dist >= 0.1 else 'odo', gps_dist, odo_dist, dur, bat, eff)

def _track_field(imei: str, field: str, val, now_ms: int):
    if imei not in _trip_fields:
        _trip_fields[imei] = {}

    fields      = _trip_fields[imei]
    prev_status = fields.get('status')
    fields[field] = val

    if field == 'status':
        prev_on = prev_status is not None and prev_status not in OFF_STATUSES
        curr_on = val is not None and val not in OFF_STATUSES
        if curr_on and not prev_on:
            _on_trip_start(imei, now_ms)
        elif prev_on and not curr_on:
            _on_trip_end(imei)

    elif field == 'speed' and imei in _trip_active and val is not None:
        speed = float(val)
        if speed > _trip_active[imei]['max_speed']:
            _trip_active[imei]['max_speed'] = speed

    elif field in ('latitude', 'longitude'):
        _maybe_add_point(imei, now_ms)

    elif field in TEMP_FIELDS and imei in _trip_active and val is not None:
        try:
            acc = _trip_active[imei]['temps'][TEMP_FIELDS[field]]
            acc[0] += float(val)
            acc[1] += 1
        except (ValueError, TypeError):
            pass

def _parse_float(raw) -> float | None:
    try:
        if raw in (None, 'None', 'null', ''):
            return None
        return float(raw)
    except (ValueError, TypeError):
        return None

# ─── MQTT ─────────────────────────────────────────────────────

def on_connect(client, userdata, connect_flags, reason_code, properties):
    logging.info('Connected: %s', reason_code)
    opts = mqtt.SubscribeOptions(qos=0, noLocal=True)
    client.subscribe([
        ('home/silence-server/+/status',   opts),
        ('home/silence-server/+/status/+', opts),
    ])

def on_message(client, userdata, msg):
    if msg.retain:
        return

    parts  = msg.topic.split('/')
    now_ms = int(time.time() * 1000)

    if len(parts) == 5 and parts[3] == 'status' and parts[4] != 'dataTimestamp':
        imei  = parts[2]
        field = parts[4]
        raw   = msg.payload.decode()
        val   = _parse_float(raw)
        if val is None and raw not in ('None', 'null', ''):
            val = raw  # keep string values (VIN, driveMode…)

        _track_field(imei, field, val, now_ms)

        if now_ms - _last_ts.get(imei, 0) > 1000:
            _last_ts[imei] = now_ms
            client.publish(f'home/silence-server/{imei}/status/dataTimestamp',
                           str(now_ms), qos=0, retain=True)

    elif len(parts) == 4 and parts[3] == 'status':
        try:
            payload = json.loads(msg.payload)
            payload['dataTimestamp'] = now_ms
            imei = parts[2]
            for field in ('status', 'speed', 'odo', 'SOCbatteria', 'BatterySoC',
                          'latitude', 'longitude'):
                if field in payload:
                    _track_field(imei, field, _parse_float(payload[field]), now_ms)
            client.publish(msg.topic, json.dumps(payload), qos=0, retain=True)
            return
        except Exception:
            pass

    client.publish(msg.topic, msg.payload, qos=0, retain=True)


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id='silence-retain-relay',
    protocol=mqtt.MQTTv5
)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_forever()

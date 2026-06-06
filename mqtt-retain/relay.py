import paho.mqtt.client as mqtt
import os
import logging
import time
import json
from datetime import datetime

_last_ts: dict[str, int] = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BROKER     = os.getenv('MQTT_HOST', 'mosquitto')
PORT       = int(os.getenv('MQTT_PORT', 1883))
DATA_DIR   = os.getenv('DATA_DIR', '/data')
TRIPS_FILE = os.path.join(DATA_DIR, 'trips.json')
MAX_TRIPS  = 100

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
_trip_active: dict[str, dict] = {}  # imei -> {start_time, start_odo, start_soc, max_speed, speeds}

def _get_soc(fields: dict) -> float:
    soc = fields.get('SOCbatteria') if fields.get('SOCbatteria') is not None else fields.get('BatterySoC')
    return float(soc) if soc is not None else 0.0

def _on_trip_start(imei: str, now_ms: int):
    fields = _trip_fields.get(imei, {})
    odo = float(fields.get('odo') or 0)
    soc = _get_soc(fields)
    _trip_active[imei] = {
        'start_time': now_ms,
        'start_odo': odo,
        'start_soc': soc,
        'max_speed': 0.0,
        'speeds': [],
        'path': [],          # GPS track: list of [lat, lon]
        'last_pt_ms': 0,     # throttle GPS sampling
    }
    logging.info('Trip started: IMEI=%s odo=%.1f soc=%.1f%%', imei, odo, soc)

PATH_INTERVAL_MS = 3000   # min delay between two recorded GPS points
MAX_PATH_POINTS  = 2000   # cap to keep trips.json reasonable

def _maybe_add_point(imei: str, now_ms: int):
    active = _trip_active.get(imei)
    if not active:
        return
    fields = _trip_fields.get(imei, {})
    lat = _parse_float(fields.get('latitude'))
    lon = _parse_float(fields.get('longitude'))
    if not lat or not lon:   # None or 0 → no GPS fix
        return
    if now_ms - active['last_pt_ms'] < PATH_INTERVAL_MS:
        return
    active['last_pt_ms'] = now_ms
    if len(active['path']) < MAX_PATH_POINTS:
        active['path'].append([round(lat, 5), round(lon, 5)])

def _on_trip_end(imei: str):
    global _all_trips
    active = _trip_active.pop(imei, None)
    if not active:
        return

    fields  = _trip_fields.get(imei, {})
    end_odo = float(fields.get('odo') or active['start_odo'])
    end_soc = _get_soc(fields)

    dist = round(end_odo - active['start_odo'], 1)
    if dist < 0.1:
        logging.info('Trip ignored (%.1f km)', dist)
        return

    dur     = max(1, round((time.time() * 1000 - active['start_time']) / 60000))
    speeds  = active['speeds']
    avg_spd = round(sum(speeds) / len(speeds)) if speeds else 0
    bat     = round(active['start_soc'] - end_soc, 1)
    dt      = datetime.fromtimestamp(active['start_time'] / 1000)

    trip = {
        'date': dt.strftime('%d/%m %H:%M'),
        'ts':   active['start_time'],
        'dur':  dur,
        'dist': str(dist),
        'bat':  str(bat),
        'vmax': round(active['max_speed']),
        'vavg': avg_spd,
        'path': active['path'],
    }

    imei_trips = _all_trips.get(imei, [])
    imei_trips.insert(0, trip)
    if len(imei_trips) > MAX_TRIPS:
        imei_trips = imei_trips[:MAX_TRIPS]
    _all_trips[imei] = imei_trips
    _save_trips(_all_trips)

    logging.info('Trip saved: IMEI=%s dist=%.1f km dur=%d min bat=%.1f%%',
                 imei, dist, dur, bat)

def _track_field(imei: str, field: str, val, now_ms: int):
    if imei not in _trip_fields:
        _trip_fields[imei] = {}

    fields      = _trip_fields[imei]
    prev_status = fields.get('status')
    fields[field] = val

    if field == 'status':
        prev_moving = (prev_status == 4)
        curr_moving = (val == 4)
        if curr_moving and not prev_moving:
            _on_trip_start(imei, now_ms)
        elif prev_moving and not curr_moving:
            _on_trip_end(imei)

    elif field == 'speed' and imei in _trip_active and val is not None:
        speed = float(val)
        _trip_active[imei]['speeds'].append(speed)
        if speed > _trip_active[imei]['max_speed']:
            _trip_active[imei]['max_speed'] = speed

    elif field in ('latitude', 'longitude'):
        _maybe_add_point(imei, now_ms)

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

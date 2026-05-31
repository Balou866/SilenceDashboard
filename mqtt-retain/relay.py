import paho.mqtt.client as mqtt
import os
import logging
import time
import json

_last_ts: dict[str, int] = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BROKER = os.getenv('MQTT_HOST', 'mosquitto')
PORT   = int(os.getenv('MQTT_PORT', 1883))

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

    parts = msg.topic.split('/')
    now_ms = int(time.time() * 1000)

    if len(parts) == 5 and parts[3] == 'status' and parts[4] != 'dataTimestamp':
        # Per-field format: stamp once per second per IMEI (batch of fields → one timestamp)
        imei = parts[2]
        if now_ms - _last_ts.get(imei, 0) > 1000:
            _last_ts[imei] = now_ms
            client.publish(f'home/silence-server/{imei}/status/dataTimestamp',
                           str(now_ms), qos=0, retain=True)
    elif len(parts) == 4 and parts[3] == 'status':
        # JSON format: inject timestamp into payload
        try:
            payload = json.loads(msg.payload)
            payload['dataTimestamp'] = now_ms
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

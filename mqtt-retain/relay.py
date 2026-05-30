import paho.mqtt.client as mqtt
import os
import logging

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
    if not msg.retain:
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

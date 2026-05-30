import paho.mqtt.client as mqtt
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BROKER = os.getenv('MQTT_HOST', 'mosquitto')
PORT   = int(os.getenv('MQTT_PORT', 1883))

# Separate publisher client — no subscriptions, no loop risk
pub = mqtt.Client(client_id='silence-retain-pub')
pub.connect(BROKER, PORT)
pub.loop_start()

def on_connect(client, userdata, flags, rc):
    logging.info('Connected rc=%d', rc)
    client.subscribe([
        ('home/silence-server/+/status',   0),
        ('home/silence-server/+/status/+', 0),
    ])

def on_message(client, userdata, msg):
    if not msg.retain:
        pub.publish(msg.topic, msg.payload, qos=0, retain=True)

sub = mqtt.Client(client_id='silence-retain-sub')
sub.on_connect = on_connect
sub.on_message = on_message
sub.connect(BROKER, PORT)
sub.loop_forever()

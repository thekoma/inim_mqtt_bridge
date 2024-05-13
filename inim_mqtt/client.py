import sys
import myconst
import time
import logging
import random
from paho.mqtt import client as mqtt_client
from datetime import datetime as dt

logger = logging.getLogger('root')
logger.debug('Loading inim module.')

MQTT_CLIENT_ID = f'publish-{random.randint(0, 1000)}'
MQTT_HOST = myconst.MQTT_HOST
MQTT_PORT = myconst.MQTT_PORT
MQTT_USER = myconst.MQTT_USER
MQTT_PASS = myconst.MQTT_PASS
MQTT_KEEPALIVE = myconst.MQTT_KEEPALIVE
MQTT_QOS = myconst.MQTT_QOS
MQTT_TOPIC = myconst.MQTT_TOPIC

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

class mqttLink:
    def __init__(
            self,
            mqtt_client_id: str = "publish-" + str(random.randint(0, 1000)),
            mqtt_host: str = myconst.MQTT_HOST,
            mqtt_port: int = myconst.MQTT_PORT,
            mqtt_user: str = myconst.MQTT_USER,
            mqtt_pass: str = myconst.MQTT_PASS,
            mqtt_keepalive: int = myconst.MQTT_KEEPALIVE,
            mqtt_qos: str = myconst.MQTT_QOS,
            mqtt_topic: str = myconst.MQTT_TOPIC,
            ):

        self.mqtt_client_id = mqtt_client_id
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.mqtt_keepalive = mqtt_keepalive
        self.mqtt_qos = mqtt_qos
        self.mqtt_topic = mqtt_topic
        global client
        self.first_reconnect_delay = 1
        self.reconnect_rate = 2
        self.max_reconnect_count = 12
        self.max_reconnect_delay = 60

    def connect_mqtt(self) -> mqtt_client:
        def on_connect(client, userdata, flags, reason_code, properties):
            if flags.session_present:
                print("Session Present!")
            if reason_code == 0:
                # success connect
                print("Connected to MQTT Broker!")
            if reason_code > 0:
                    print(f"Failed to connect, return code {reason_code}")
                # error processing

        def on_disconnect(client, userdata, rc):
            logging.info("Disconnected with result code: %s", rc)
            reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
            while reconnect_count < MAX_RECONNECT_COUNT:
                logging.info("Reconnecting in %d seconds...", reconnect_delay)
                time.sleep(reconnect_delay)

                try:
                    client.reconnect()
                    logging.info("Reconnected successfully!")
                    return
                except Exception as err:
                    logging.error("%s. Reconnect failed. Retrying...", err)

                reconnect_delay *= self.reconnect_rate
                reconnect_delay = min(reconnect_delay, self.max_reconnect_delay)
                reconnect_count += 1
            logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, self.mqtt_client_id)
        client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.connect(self.mqtt_host, self.mqtt_port, self.mqtt_keepalive)
        client.loop_start()
        return client

    # def publish(self, client, message: str = None):
    def publish(self, client, message: str = None, topic: str = None):
        if topic is None:
            topic = self.mqtt_topic
        result = client.publish(topic, message)
        status = result[0]
        if status == 0:
            print(f"Send `{message}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic {topic}")

    def subscribe(self, client: mqtt_client):
        def on_message(client, userdata, msg):
            print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        client.subscribe(self.mqtt_topic)
        client.on_message = on_message

    def start(self):
        client = self.connect_mqtt()
        self.subscribe(client)
        client.loop_start()
        # self.publish(client)
        return client
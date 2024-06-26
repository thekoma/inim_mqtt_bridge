import sys
import myconst
import time
import logging
import random
from paho.mqtt import client as mqtt_client
from datetime import datetime as dt
import paho.mqtt

logger = logging.getLogger('root')
logger.debug('Loading mqtt module.')

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
        print(f"MQTT_HOST: {self.mqtt_host}")
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.mqtt_keepalive = mqtt_keepalive
        self.mqtt_qos = mqtt_qos
        self.mqtt_topic = mqtt_topic
        self.first_reconnect_delay = 1
        self.reconnect_rate = 2
        self.max_reconnect_count = 12
        self.max_reconnect_delay = 60
        self.m_client = None

    def connect_mqtt(self) -> mqtt_client:
        def on_connect(m_client, userdata, flags, reason_code, properties=None):
            if reason_code == 0:
                # success connect
                logger.info("Connected to MQTT Broker!")
            if reason_code > 0:
                    logger.error(f"Failed to connect, return code {reason_code}")


        def on_disconnect(m_client, userdata,  flags, reason_code, properties):
            logger.info(f"Disconnected with result code: {reason_code}")
            reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
            while reconnect_count < MAX_RECONNECT_COUNT:
                logger.info("Reconnecting in %d seconds...", reconnect_delay)
                time.sleep(reconnect_delay)

                try:
                    self.m_client.reconnect()
                    logger.info("Reconnected successfully!")
                    return
                except Exception as err:
                    logger.error("%s. Reconnect failed. Retrying...", err)

                reconnect_delay *= self.reconnect_rate
                reconnect_delay = min(reconnect_delay, self.max_reconnect_delay)

            logger.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)
            sys.exit(188)



        logger.debug("Creating MQTT client")
        self.m_client = mqtt_client.Client(self.mqtt_client_id)
        self.m_client.on_connect = on_connect
        self.m_client.on_disconnect = on_disconnect
        self.m_client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        logger.info(f"Connecting to {self.mqtt_host}")
        self.m_client.connect(self.mqtt_host, self.mqtt_port, self.mqtt_keepalive)
        self.m_client.loop_start()
        return self.m_client

    # def publish(self, client, message: str = None):
    def publish(self, message: str = None, topic: str = None):
        if topic is None:
            topic = self.mqtt_topic
        result = self.m_client.publish(topic, message)
        status = result[0]
        if status == 0:
            print(f"Send `{message}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic {topic}")

    def subscribe(self, client: mqtt_client):
        def on_message(client, userdata, msg):
            logger.debug(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        the_client=self.m_client
        the_client.subscribe(self.mqtt_topic)
        the_client.on_message = on_message

    def start(self):
        client = self.connect_mqtt()
        self.subscribe(self.m_client)
        return client

    def stop(self):
        self.m_client.loop_stop()
        self.m_client.disconnect()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.stop()
        time.sleep(0)